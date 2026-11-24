"""add note folders and notes

Notes live in user-made folders and are listed as a date timeline. Folders are
separate from study domains on purpose: deleting a domain should not take a
diary entry with it.

Revision ID: b8e4f72c39a1
Revises: a5c3e81f60d9
Create Date: 2026-11-24 12:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8e4f72c39a1'
down_revision: Union[str, None] = 'a5c3e81f60d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "note_folders" not in tables:
        op.create_table(
            "note_folders",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_note_folders_user_id"),
            "note_folders",
            ["user_id"],
            unique=False,
        )

    if "notes" not in tables:
        op.create_table(
            "notes",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("folder_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["folder_id"], ["note_folders.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notes_folder_id"), "notes", ["folder_id"], unique=False)
        op.create_index(op.f("ix_notes_user_id"), "notes", ["user_id"], unique=False)
        op.create_index(op.f("ix_notes_created_at"), "notes", ["created_at"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "notes" in tables:
        op.drop_index(op.f("ix_notes_created_at"), table_name="notes")
        op.drop_index(op.f("ix_notes_user_id"), table_name="notes")
        op.drop_index(op.f("ix_notes_folder_id"), table_name="notes")
        op.drop_table("notes")

    if "note_folders" in tables:
        op.drop_index(op.f("ix_note_folders_user_id"), table_name="note_folders")
        op.drop_table("note_folders")
