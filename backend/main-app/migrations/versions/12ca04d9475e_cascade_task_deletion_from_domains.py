"""cascade task deletion from domains

Deleting a domain used to raise a foreign-key error if it still had tasks,
because tasks.domain_id had no ON DELETE CASCADE. This replaces the
constraint so the delete succeeds and removes the tasks with it.

Revision ID: 12ca04d9475e
Revises: 56b406e8eefc
Create Date: 2026-11-23 18:33:21.986280
"""
from typing import Sequence, Union

from alembic import op

revision: str = '12ca04d9475e'
down_revision: Union[str, None] = '56b406e8eefc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Named explicitly so both upgrade and downgrade can drop it reliably.
CONSTRAINT = "tasks_domain_id_fkey"


def upgrade() -> None:
    # Speeds up the cascade lookup.
    op.create_index("ix_tasks_domain_id", "tasks", ["domain_id"], unique=False)

    op.drop_constraint(CONSTRAINT, "tasks", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT,
        "tasks",
        "domains",
        ["domain_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, "tasks", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT,
        "tasks",
        "domains",
        ["domain_id"],
        ["id"],
    )
    op.drop_index("ix_tasks_domain_id", table_name="tasks")
