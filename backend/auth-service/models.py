from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Uuid, func
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

    # This model defines a required string column for storing the password hash.
    # Hashing and encryption aren't the same. Encryption is designed to be reversible with a key; 
    # password hashing is designed for verification without recovering the original password.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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
