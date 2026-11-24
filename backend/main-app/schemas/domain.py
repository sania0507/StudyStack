import uuid
from pydantic import BaseModel


class DomainCreate(BaseModel):
    name: str
    # Mark a domain as a daily routine when you create it.
    repeats_daily: bool = False


class DomainUpdate(BaseModel):
    name: str | None = None
    colour: str | None = None
    repeats_daily: bool | None = None


class DomainOut(BaseModel):
    id: uuid.UUID
    name: str
    colour: str
    user_id: uuid.UUID
    repeats_daily: bool

    model_config = {"from_attributes": True}
