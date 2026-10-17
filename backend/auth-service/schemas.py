from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict
# EmailStr is a special Pydantic type that validates whether a value looks like a valid email address.

#UserCreate
#INPUT: what the client sends to StudyStack.
class UserCreate(BaseModel):
    email: EmailStr
    password: str

#UserOut
#OUTPUT: what StudyStack sends back. Hence needs ConfigDict to take info from database and validate it using Pydantic.
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True) 
    # SQLAlchemy provides the object; Pydantic validates and serializes it.
    # from_attributes=True lets Pydantic read the object's attributes.
    # It doesn't validate the database itself or fetch information from PostgreSQL.

    id: UUID
    email: EmailStr
    created_at: datetime

class LoginRequest(BaseModel): 
    # This represents the data the frontend sends when a user attempts to log in.
    email: EmailStr
    password: str




class Token(BaseModel):
    # This represents the response the backend sends after successful authentication.
    
    access_token: str # access_token holds the JWT.
    token_type: str = "bearer" # token_type tells the client what kind of token it received.

