import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    domain_id: uuid.UUID
    title: str
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None
    due_date: datetime | None = None


class TaskOut(BaseModel):
    id: uuid.UUID
    domain_id: uuid.UUID
    title: str
    completed: bool
    completed_at: datetime | None
    due_date: datetime | None
    overdue: bool
    # The soonest reminder still waiting to fire, so the UI can show a bell.
    next_reminder_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }

