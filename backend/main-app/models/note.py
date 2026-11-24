import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class NoteFolder(Base):
    """A user-made drawer for notes: DSA, dev, diary, whatever they want.

    Modelled like `domains` — owned by a user, no cross-user visibility — but
    deliberately separate, because deleting a study domain should not take a
    diary entry with it.
    """

    __tablename__ = "note_folders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Note(Base):
    """One note. Body is plain text; markdown is rendered by the client."""

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    folder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("note_folders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalised owner, so every query can be scoped without a join. A note is
    # never visible to anyone but its owner, and this makes that one predicate.
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Pinned notes sit above the timeline regardless of date.
    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
