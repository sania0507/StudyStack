from datetime import datetime
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("domains.id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(nullable=False)

    completed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )

    due_date: Mapped[datetime | None] = mapped_column(
        nullable=True
    )