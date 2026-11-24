"""add recurring domains and the completion log

repeats_daily on domains marks a routine; task_completions records which task
was finished on which day so a daily reset never destroys history.

Revision ID: e7b1c93f2a48
Revises: 12ca04d9475e
Create Date: 2026-11-24 12:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e7b1c93f2a48'
down_revision: Union[str, None] = '12ca04d9475e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    domain_columns = {c["name"] for c in inspector.get_columns("domains")}

    if "repeats_daily" not in domain_columns:
        op.add_column(
            "domains",
            sa.Column(
                "repeats_daily",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    if "task_completions" not in inspector.get_table_names():
        op.create_table(
            "task_completions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("task_id", sa.Uuid(), nullable=False),
            sa.Column("completed_on", sa.Date(), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("task_id", "completed_on", name="uq_task_completion_day"),
        )
        op.create_index(
            op.f("ix_task_completions_task_id"),
            "task_completions",
            ["task_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_task_completions_completed_on"),
            "task_completions",
            ["completed_on"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "task_completions" in inspector.get_table_names():
        op.drop_index(op.f("ix_task_completions_completed_on"), table_name="task_completions")
        op.drop_index(op.f("ix_task_completions_task_id"), table_name="task_completions")
        op.drop_table("task_completions")

    domain_columns = {c["name"] for c in inspector.get_columns("domains")}
    if "repeats_daily" in domain_columns:
        op.drop_column("domains", "repeats_daily")
