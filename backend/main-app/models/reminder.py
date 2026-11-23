from datetime import datetime
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    remind_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    # sent_at stays NULL until the scheduler processes the reminder.
    # The worker uses it to make sure one reminder is never sent twice.
    sent_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )
