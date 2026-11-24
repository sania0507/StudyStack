import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)


class FolderOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    # How many notes live here, so the rail can show a count without a second
    # request per folder.
    note_count: int = 0

    model_config = {"from_attributes": True}


class NoteCreate(BaseModel):
    folder_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    pinned: bool = False


class NoteUpdate(BaseModel):
    # folder_id is included so a note can be dragged to another folder.
    folder_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    pinned: bool | None = None


class ReorderNotes(BaseModel):
    """A drag-and-drop drops a whole new order for one list at once."""

    note_ids: list[uuid.UUID] = Field(min_length=1)


class NoteOut(BaseModel):
    id: uuid.UUID
    folder_id: uuid.UUID
    title: str
    body: str
    pinned: bool
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
