"""add vision item width

Tiles were a fixed pixel size. Width is now a percentage of the board, so a
resized tile keeps its proportion on any screen.

Revision ID: a5c3e81f60d9
Revises: f2a9d47c81b3
Create Date: 2026-11-24 12:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a5c3e81f60d9'
down_revision: Union[str, None] = 'f2a9d47c81b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("vision_items")}

    if "width" not in columns:
        # 16 matches the old fixed size on a typical board, so existing tiles
        # do not jump when this ships.
        op.add_column(
            "vision_items",
            sa.Column("width", sa.Float(), nullable=False, server_default="16"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("vision_items")}

    if "width" in columns:
        op.drop_column("vision_items", "width")
