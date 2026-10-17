import uuid
from pydantic import BaseModel


class DomainCreate(BaseModel):
    name: str


class DomainUpdate(BaseModel):
    name: str | None = None
    colour: str | None = None


class DomainOut(BaseModel):
    id: uuid.UUID
    name: str
    colour: str
    user_id: uuid.UUID

    model_config = {"from_attributes": True}
