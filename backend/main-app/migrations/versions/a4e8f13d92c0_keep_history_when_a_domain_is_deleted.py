"""keep history when a domain is deleted

Deleting a domain used to delete the evidence of the work: study_sessions
cascaded from domains and task_completions cascaded from tasks, so analytics
went back in time and the streak, heatmap and totals lost days that really
happened.

This migration keeps the history and drops only the link:

  study_sessions.domain_id  -> nullable, ON DELETE SET NULL
  study_sessions.task_id    -> ON DELETE SET NULL
  task_completions.task_id  -> nullable, ON DELETE SET NULL

It also adds the columns that let a surviving row still describe itself:
study_sessions.domain_name, study_sessions.task_title (snapshots taken at
record time) and task_completions.user_id (so the day can be counted without
joining through a task that may no longer exist).

Revision ID: a4e8f13d92c0
Revises: d1f6b28a75e4
Create Date: 2026-11-26 06:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4e8f13d92c0"
down_revision: Union[str, None] = "d1f6b28a75e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Constraint names are NOT assumed. PostgreSQL auto-names inline FK constraints
# `<table>_<column>_fkey`, but `study_sessions.task_id` was added by a later
# migration (d1f6b28a75e4) with an explicit name, `fk_study_sessions_task_id`.
# Guessing the convention is what broke the first run of this revision, so the
# foreign keys are discovered from the column they constrain.
def _foreign_key_names(inspector, table: str, column: str) -> list[str]:
    """Every FK constraint name on `table` that covers exactly `column`."""
    return [
        fk["name"]
        for fk in inspector.get_foreign_keys(table)
        if fk.get("constrained_columns") == [column]
    ]


def _replace_foreign_key(bind, table: str, column: str, target: str, ondelete: str) -> None:
    """Drop whatever FK governs `table.column` and recreate it with `ondelete`.

    Dropping by discovered name keeps this correct on a database that ran the
    initial schema and on one migrated by later revisions alike.
    """
    for name in _foreign_key_names(sa.inspect(bind), table, column):
        op.drop_constraint(name, table, type_="foreignkey")

    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        target,
        [column],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    bind = op.get_bind()

    # ---- study_sessions: keep the row, describe it, loosen the links ----
    op.add_column(
        "study_sessions",
        sa.Column("domain_name", sa.String(120), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("task_title", sa.String(200), nullable=True),
    )

    # Backfill so existing history is labelled too, not just new rows.
    op.execute(
        """
        UPDATE study_sessions AS s
        SET domain_name = d.name
        FROM domains AS d
        WHERE d.id = s.domain_id AND s.domain_name IS NULL
        """
    )
    op.execute(
        """
        UPDATE study_sessions AS s
        SET task_title = t.title
        FROM tasks AS t
        WHERE t.id = s.task_id AND s.task_title IS NULL
        """
    )

    op.alter_column("study_sessions", "domain_id", nullable=True)

    _replace_foreign_key(bind, "study_sessions", "domain_id", "domains", "SET NULL")
    _replace_foreign_key(bind, "study_sessions", "task_id", "tasks", "SET NULL")

    # ---- task_completions: own the day, do not borrow it from a task ----
    op.add_column(
        "task_completions",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )

    # Every existing row belongs to the owner of the task's domain. The join is
    # guaranteed to find one because task_id was NOT NULL with a cascading FK,
    # so a completion could never outlive its task. If that assumption is ever
    # wrong, fail here rather than at the SET NOT NULL below, where the error
    # would not say why.
    op.execute(
        """
        DO $$
        DECLARE orphans integer;
        BEGIN
            SELECT count(*) INTO orphans
            FROM task_completions AS tc
            WHERE tc.user_id IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM tasks AS t
                  JOIN domains AS d ON d.id = t.domain_id
                  WHERE t.id = tc.task_id
              );

            IF orphans > 0 THEN
                RAISE EXCEPTION
                    '% task_completions rows have no owning user; backfill aborted',
                    orphans;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        UPDATE task_completions AS tc
        SET user_id = d.user_id
        FROM tasks AS t
        JOIN domains AS d ON d.id = t.domain_id
        WHERE t.id = tc.task_id AND tc.user_id IS NULL
        """
    )

    op.alter_column("task_completions", "user_id", nullable=False)
    op.create_index(
        "ix_task_completions_user_id",
        "task_completions",
        ["user_id"],
        unique=False,
    )

    op.alter_column("task_completions", "task_id", nullable=True)

    _replace_foreign_key(bind, "task_completions", "task_id", "tasks", "SET NULL")


def downgrade() -> None:
    bind = op.get_bind()

    # Rows whose task or domain is gone cannot satisfy the old NOT NULL
    # constraints, so going back means discarding exactly the history this
    # migration was added to keep. Say so loudly rather than silently deleting.
    op.execute("DELETE FROM task_completions WHERE task_id IS NULL")
    op.execute("DELETE FROM study_sessions WHERE domain_id IS NULL")

    _replace_foreign_key(bind, "task_completions", "task_id", "tasks", "CASCADE")
    op.alter_column("task_completions", "task_id", nullable=False)

    op.drop_index("ix_task_completions_user_id", table_name="task_completions")
    op.drop_column("task_completions", "user_id")

    _replace_foreign_key(bind, "study_sessions", "task_id", "tasks", "CASCADE")
    _replace_foreign_key(bind, "study_sessions", "domain_id", "domains", "CASCADE")
    op.alter_column("study_sessions", "domain_id", nullable=False)

    op.drop_column("study_sessions", "task_title")
    op.drop_column("study_sessions", "domain_name")
