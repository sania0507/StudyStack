import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional: a timed block can target one task. When it does, "how long did
    # chapter 3 actually take" becomes answerable, which minutes-per-domain
    # never could. Left nullable so "just start focusing" still works.
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Stored in seconds. Minutes lost everything under a minute and could not
    # distinguish a 5-second test from a 5-minute block.
    duration_seconds: Mapped[int] = mapped_column(nullable=False)

    finished_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )
