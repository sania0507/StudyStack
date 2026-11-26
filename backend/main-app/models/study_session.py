import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    # SET NULL, not CASCADE: deleting a domain must not delete the hours you
    # spent on it. The session survives as history with the link removed, and
    # domain_name below keeps the label so analytics can still say what it was.
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Snapshot taken when the block is recorded, because the domain may be gone
    # by the time the feed is drawn.
    domain_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    # Optional: a timed block can target one task. When it does, "how long did
    # chapter 3 actually take" becomes answerable, which minutes-per-domain
    # never could. Also SET NULL, for the same reason as domain_id.
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    task_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Stored in seconds. Minutes lost everything under a minute and could not
    # distinguish a 5-second test from a 5-minute block.
    duration_seconds: Mapped[int] = mapped_column(nullable=False)

    finished_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )
