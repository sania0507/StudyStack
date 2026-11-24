import uuid

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VisionItem(Base):
    """One image on a user's vision board.

    Images are stored as bytes rather than as a remote URL. A pasted Pinterest
    link is fetched once, on save, and the bytes are kept here: Pinterest image
    URLs expire, so a board holding only links would quietly develop holes.

    x/y are the free drag-and-drop position, in percentage of the board so the
    layout survives different screen widths.
    """

    __tablename__ = "vision_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    caption: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    image_mime: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    image_data: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    # Where the user dropped it, 0..100 in both axes.
    x: Mapped[float] = mapped_column(default=0.0, nullable=False)
    y: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Width as a percentage of the board, so a resized tile keeps its
    # proportion on a phone. Height follows the image's own aspect ratio.
    width: Mapped[float] = mapped_column(
        default=16.0,
        nullable=False,
        server_default="16",
    )
