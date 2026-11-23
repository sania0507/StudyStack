import uuid
from datetime import datetime

from pydantic import BaseModel


class ReminderCreate(BaseModel):
    task_id: uuid.UUID
    remind_at: datetime


class ReminderUpdate(BaseModel):
    remind_at: datetime | None = None


class ReminderOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    remind_at: datetime
    sent_at: datetime | None

    model_config = {
        "from_attributes": True
    }
