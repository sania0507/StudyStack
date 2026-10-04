import uuid

from pydantic import BaseModel


class SubtaskCreate(BaseModel):
    task_id: uuid.UUID
    title: str


class SubtaskUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


class SubtaskOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    title: str
    completed: bool

    model_config = {
        "from_attributes": True
    }