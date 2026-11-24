"""add avatar columns

The initial revision already creates these columns, but production applied that
revision before they existed, so a deployed database needs this explicit step.

Revision ID: c4f8a2d61b57
Revises: a1d4c7e9b210
Create Date: 2026-11-24 11:58:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4f8a2d61b57'
down_revision: Union[str, None] = 'a1d4c7e9b210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("users")}

    # Idempotent: a fresh database gets both columns from the initial revision,
    # so this must not fail there.
    if "avatar_mime" not in existing:
        op.add_column("users", sa.Column("avatar_mime", sa.String(length=64), nullable=True))

    if "avatar_data" not in existing:
        op.add_column("users", sa.Column("avatar_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("users")}

    if "avatar_data" in existing:
        op.drop_column("users", "avatar_data")

    if "avatar_mime" in existing:
        op.drop_column("users", "avatar_mime")
