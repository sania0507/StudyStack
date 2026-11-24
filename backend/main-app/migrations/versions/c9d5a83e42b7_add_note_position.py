"""add note position

Manual drag-and-drop order for notes. created_at stays untouched: the date a
note was written is a fact, and dragging only changes where it sits.

Revision ID: c9d5a83e42b7
Revises: b8e4f72c39a1
Create Date: 2026-11-24 13:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c9d5a83e42b7'
down_revision: Union[str, None] = 'b8e4f72c39a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("notes")}

    if "position" not in columns:
        # 0 for every existing note, so the date tie-break keeps the current
        # order until the user drags something.
        op.add_column(
            "notes",
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("notes")}

    if "position" in columns:
        op.drop_column("notes", "position")
