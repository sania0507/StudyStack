import uuid

from pydantic import BaseModel, Field


class VisionItemCreateFromUrl(BaseModel):
    """Add by pasting a link. The server fetches it once and stores the bytes."""

    image_url: str
    caption: str | None = Field(default=None, max_length=200)


class VisionItemUpdate(BaseModel):
    """Moving or re-captioning an item. Positions are percentages."""

    x: float | None = Field(default=None, ge=0, le=100)
    y: float | None = Field(default=None, ge=0, le=100)
    caption: str | None = Field(default=None, max_length=200)
    # 6% is a thumbnail, 60% is most of the wall. Bounded so a tile can never
    # be resized to nothing or past the edge.
    width: float | None = Field(default=None, ge=6, le=60)


class VisionItemOut(BaseModel):
    id: uuid.UUID
    caption: str | None
    # The bytes are served by /vision-items/{id}/image, so the board payload
    # stays small no matter how many images it holds.
    x: float
    y: float
    width: float

    model_config = {"from_attributes": True}
