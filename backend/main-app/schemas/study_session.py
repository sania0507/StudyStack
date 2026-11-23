import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StudySessionCreate(BaseModel):
    domain_id: uuid.UUID

    # A session of zero minutes or less is not a real study session.
    minutes: int = Field(gt=0)


class StudySessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    domain_id: uuid.UUID
    minutes: int
    finished_at: datetime

    model_config = {
        "from_attributes": True
    }
