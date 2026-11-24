from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict

from models import User
# EmailStr is a special Pydantic type that validates whether a value looks like a valid email address.

#UserCreate
#INPUT: what the client sends to StudyStack.
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    # Optional: registration works without a name.
    name: str | None = None

#UserOut
#OUTPUT: what StudyStack sends back. Hence needs ConfigDict to take info from database and validate it using Pydantic.
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True) 
    # SQLAlchemy provides the object; Pydantic validates and serializes it.
    # from_attributes=True lets Pydantic read the object's attributes.
    # It doesn't validate the database itself or fetch information from PostgreSQL.

    id: UUID
    email: EmailStr
    name: str | None = None
    created_at: datetime
    # A flag, not the image: the bytes are served by GET /auth/me/avatar so
    # they can be cached by the browser instead of riding on every payload.
    # Derived in the handler, since there is no has_avatar column.
    has_avatar: bool = False

    @classmethod
    def from_user(cls, user: "User") -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            has_avatar=user.avatar_data is not None,
        )


class UserUpdate(BaseModel):
    # Both fields are optional, so the client can change just one.
    name: str | None = None
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class LoginRequest(BaseModel): 
    # This represents the data the frontend sends when a user attempts to log in.
    email: EmailStr
    password: str




class Token(BaseModel):
    # This represents the response the backend sends after successful
    # authentication.
    access_token: str # access_token holds the short-lived JWT.
    # The access token expires in minutes; the refresh token buys a new one
    # without asking for the password again.
    refresh_token: str
    token_type: str = "bearer" # token_type tells the client what kind of token it received.


class RefreshRequest(BaseModel):
    refresh_token: str

