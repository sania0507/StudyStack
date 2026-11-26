from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    domain_id: Mapped[uuid.UUID] = mapped_column(
        # CASCADE so deleting a domain removes its tasks instead of raising a
        # foreign-key error. Subtasks, reminders and sessions then cascade from
        # the task in turn.
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(nullable=False)

    completed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    # Both are instants, so both are timestamptz. A naive column would hold the
    # writer's wall clock, and comparing it against an aware "now" raises
    # TypeError in Python and shifts the answer in SQL.
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )