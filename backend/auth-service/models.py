from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid
from datetime import datetime
from sqlalchemy import LargeBinary, String, DateTime, Uuid, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4, #call this (function=uuid, method= uuid4) when a default value is needed
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Optional display name. When it is missing the frontend falls back to
    # the part of the email before the @.
    name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    # This model defines a required string column for storing the password hash.
    # Hashing and encryption aren't the same. Encryption is designed to be reversible with a key; 
    # password hashing is designed for verification without recovering the original password.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # The avatar lives in the database rather than object storage: one extra
    # column beats a second service and its credentials, and the image is
    # resized to ~256px in the browser before upload so rows stay small.
    avatar_mime: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    avatar_data: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(), 
        #when created_at hasn't been provided, PostgreSQL supplies the timestamp 
        #when it processes the insert by using server_default=func.now(). 
        #This ensures that the created_at field is always populated with the correct timestamp,
        # even if the application doesn't explicitly provide a value for it.
        nullable=False,
    )


class RefreshToken(Base):
    """One issued refresh token, stored hashed.

    Rotation rules live in auth.py; this table only records state:
    - token_hash is unique, so a token can be looked up in one query.
    - family_id groups every token descended from one login. Reuse of a
      rotated token revokes the whole family, because if a token is presented
      twice either the client or an attacker holds it, and there is no way to
      tell which from a single row.
    - revoked_at being non-null is the only thing that makes a token unusable.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Which token replaced this one during rotation, for auditing.
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
