import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskCompletion(Base):
    """One row per (task, day) on which the task was finished.

    This exists because a recurring task's `completed` flag is per-day, not
    permanent: it is unticked at the start of each new day. Keeping the history
    here means the heatmap and streaks can still count what was done, and a
    reset never destroys evidence of the work.

    The unique constraint is what makes "ticked twice in one day" impossible.
    """

    __tablename__ = "task_completions"
    __table_args__ = (
        UniqueConstraint("task_id", "completed_on", name="uq_task_completion_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    completed_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
