"""add vision items

The motivation board: images belong to a user, stored as bytes because remote
image URLs (Pinterest especially) expire, with x/y percentage positions for
free drag-and-drop.

Revision ID: f2a9d47c81b3
Revises: e7b1c93f2a48
Create Date: 2026-11-24 12:22:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f2a9d47c81b3'
down_revision: Union[str, None] = 'e7b1c93f2a48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "vision_items" in inspector.get_table_names():
        return

    op.create_table(
        "vision_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("caption", sa.String(length=200), nullable=True),
        sa.Column("image_mime", sa.String(length=64), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("y", sa.Float(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vision_items_user_id"),
        "vision_items",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "vision_items" not in inspector.get_table_names():
        return

    op.drop_index(op.f("ix_vision_items_user_id"), table_name="vision_items")
    op.drop_table("vision_items")
