from datetime import datetime
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# This > creates our application's base class, ITS the foundation from which further ORM models are declared.
class Base(DeclarativeBase):
    pass


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    colour: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("domains.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(nullable=False)

    completed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )

    due_date: Mapped[datetime | None] = mapped_column(
        nullable=True
    )


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

    minutes: Mapped[int] = mapped_column(nullable=False)

    finished_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )
