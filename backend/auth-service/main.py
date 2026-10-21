from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from auth import create_access_token, get_current_user
from database import engine, get_db
from models import Base, User
from schemas import LoginRequest, Token, UserCreate, UserOut
from security import hash_password, verify_password


app = FastAPI(title="StudyStack Auth Service")


# Creates database tables that do not exist yet.
# Useful during local development; use Alembic migrations as the project matures.
# Base.metadata.create_all(bind=engine)


@app.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    # query() creates a query for the User model.
    # filter() restricts results to users with the submitted email.
    # first() returns the first match or None if no match exists.
    existing_user = (
        db.query(User)
        .filter(User.email == user_create.email)
        .first()
    )

    # HTTPException stops execution and returns an HTTP error response.
    # 409 Conflict means an account with this email already exists.
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash the submitted password before storing anything.
    # Never store the original password in the database.
    new_user = User(
        email=str(user_create.email),
        password_hash=hash_password(user_create.password),
    )

    try:
        # add() stages the new ORM object in the database session.
        db.add(new_user)

        # commit() commits the transaction and persists the new user.
        db.commit()

        # refresh() reloads database-generated values into the Python object,
        # such as the ID and created_at timestamp.
        db.refresh(new_user)

    except IntegrityError:
        # The database can reject the insert, for example if another
        # request registers the same email at almost the same time.
        # rollback() clears the failed transaction so the session can recover.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None

    # FastAPI uses UserOut to serialize safe user information into JSON.
    # The password hash is not included in the response.
    return new_user


@app.post("/auth/login", response_model=Token)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    # Find the account associated with the submitted email.
    user = (
        db.query(User)
        .filter(User.email == credentials.email)
        .first()
    )

    # Reject missing accounts and incorrect passwords with the same
    # generic message so the endpoint does not reveal which emails exist.
    if user is None or not verify_password(
        credentials.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate a signed JWT containing the authenticated user's ID.
    access_token = create_access_token(str(user.id))

    # Token defines the response structure.
    # The client receives the token, not the user's password or hash.
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/me", response_model=UserOut)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    # Depends(get_current_user) runs the authentication dependency first.
    # It verifies the supplied Bearer token and retrieves the user.
    # If authentication fails, the dependency raises 401 and this function
    # does not execute.
    return current_user
