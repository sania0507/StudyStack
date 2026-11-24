"""record sessions in seconds, optionally against a task

minutes could not distinguish a 5-second block from a 5-minute one, and a
session attached to a domain alone could not answer "how long did this task
actually take".

Revision ID: d1f6b28a75e4
Revises: c9d5a83e42b7
Create Date: 2026-11-24 13:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd1f6b28a75e4'
down_revision: Union[str, None] = 'c9d5a83e42b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"]: c for c in inspector.get_columns("study_sessions")}

    if "task_id" not in columns:
        op.add_column(
            "study_sessions",
            sa.Column("task_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_study_sessions_task_id",
            "study_sessions",
            "tasks",
            ["task_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            op.f("ix_study_sessions_task_id"),
            "study_sessions",
            ["task_id"],
            unique=False,
        )

    if "duration_seconds" not in columns:
        op.add_column(
            "study_sessions",
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
        )

        # Existing rows keep their meaning: one minute recorded becomes 60
        # seconds. Done in SQL so no row is left null and the column can then
        # be made NOT NULL.
        if "minutes" in columns:
            op.execute(
                "UPDATE study_sessions SET duration_seconds = minutes * 60"
            )

        op.execute(
            "UPDATE study_sessions SET duration_seconds = 0 "
            "WHERE duration_seconds IS NULL"
        )
        op.alter_column("study_sessions", "duration_seconds", nullable=False)

    if "minutes" in columns:
        op.drop_column("study_sessions", "minutes")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"]: c for c in inspector.get_columns("study_sessions")}

    if "minutes" not in columns:
        op.add_column(
            "study_sessions",
            sa.Column("minutes", sa.Integer(), nullable=True),
        )
        if "duration_seconds" in columns:
            # Round up: a 40-second block was a minute of work, not zero.
            op.execute(
                "UPDATE study_sessions SET minutes = "
                "CEIL(duration_seconds / 60.0)::int"
            )
        op.execute("UPDATE study_sessions SET minutes = 0 WHERE minutes IS NULL")
        op.alter_column("study_sessions", "minutes", nullable=False)

    if "duration_seconds" in columns:
        op.drop_column("study_sessions", "duration_seconds")

    if "task_id" in columns:
        op.drop_index(op.f("ix_study_sessions_task_id"), table_name="study_sessions")
        op.drop_constraint(
            "fk_study_sessions_task_id", "study_sessions", type_="foreignkey"
        )
        op.drop_column("study_sessions", "task_id")
