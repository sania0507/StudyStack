import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StudySessionCreate(BaseModel):
    domain_id: uuid.UUID

    # Optional: record the block against one task so per-task time is possible.
    task_id: uuid.UUID | None = None

    # Seconds, not minutes: a 40-second block is a real (if short) session, and
    # rounding it to a minute lost information nobody could recover.
    duration_seconds: int = Field(gt=0, le=24 * 3600)


class StudySessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    # Null once the domain has been deleted: the block stays, the link goes.
    domain_id: uuid.UUID | None
    task_id: uuid.UUID | None
    # Snapshots taken when the block was recorded, so the activity feed can
    # still say what a deleted-domain session was.
    domain_name: str | None = None
    task_title: str | None = None
    duration_seconds: int
    finished_at: datetime

    model_config = {
        "from_attributes": True
    }
