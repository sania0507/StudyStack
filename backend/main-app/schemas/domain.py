import uuid

from pydantic import BaseModel


class DomainCreate(BaseModel):
    name: str


class DomainUpdate(BaseModel):
    name: str | None = None
    colour: str | None = None


# Pydantic needs to be told that DomainOut can read attributes from an ORM object.
# Now, pydantic can build a response from object's attributes like domain.name (from_attributes=true) instead of expecting a dictionary.
class DomainOut(BaseModel):
    id: uuid.UUID
    name: str
    colour: str

    model_config = {
        "from_attributes": True  #
    }