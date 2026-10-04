import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Subtask(Base):
    __tablename__ = "subtasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(nullable=False)

    completed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )