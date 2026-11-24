from sqlalchemy.orm import Mapped, mapped_column
import uuid

from .base import Base

class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    colour: Mapped[str] = mapped_column(nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    # A recurring domain is a routine: its tasks are things you do again every
    # day (five prayers, four revision blocks). Yesterday's ticks are kept in
    # task_completions, so resetting the tasks loses no history.
    repeats_daily: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
