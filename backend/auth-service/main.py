from fastapi import Depends, FastAPI, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from auth import (
    get_current_user,
    issue_token_pair,
    revoke_all_for_user,
    revoke_one,
    rotate_refresh_token,
)
from database import engine, get_db
from models import Base, User
from schemas import (
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    Token,
    UserCreate,
    UserOut,
    UserUpdate,
)
from security import hash_password, verify_password
from settings import settings


app = FastAPI(title="StudyStack Auth Service")

# The frontend runs on a different origin, so the browser needs these
# headers before it will accept a login response.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        name=user_create.name.strip() if user_create.name else None,
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
    return UserOut.from_user(new_user)


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

    # Two tokens: a short-lived access token for every request, and a
    # long-lived refresh token that can be exchanged once for a new pair.
    access_token, refresh_token = issue_token_pair(db, user.id)

    # Token defines the response structure.
    # The client receives the tokens, not the user's password or hash.
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
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
    return UserOut.from_user(current_user)


@app.patch("/auth/me", response_model=UserOut)
def update_current_user(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only touch the fields the client actually sent.
    if update.name is not None:
        cleaned_name = update.name.strip()

        # An empty name means "clear it", which is stored as NULL.
        current_user.name = cleaned_name or None

    if update.email is not None:
        new_email = str(update.email)

        if new_email != current_user.email:
            taken = (
                db.query(User)
                .filter(User.email == new_email)
                .first()
            )

            if taken is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

            current_user.email = new_email

    try:
        db.commit()
    except IntegrityError:
        # Another request claimed the same email between the check and commit.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None

    db.refresh(current_user)

    return UserOut.from_user(current_user)


@app.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # The current password must be proved before it can be replaced.
    if not verify_password(
        payload.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="New password must be at least 8 characters",
        )

    current_user.password_hash = hash_password(payload.new_password)

    db.commit()

    # Changing a password ends every other session: if the reason for the
    # change is a suspected compromise, leaving old refresh tokens alive would
    # defeat the point.
    revoke_all_for_user(db, current_user.id)

    return None


@app.post("/auth/refresh", response_model=Token)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Exchanges a refresh token for a new pair.

    The presented token is revoked in the same transaction that issues its
    replacement, so each refresh token works exactly once.
    """
    access_token, refresh_token = rotate_refresh_token(
        db,
        payload.refresh_token,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Revokes the presented refresh token.

    Idempotent and unauthenticated on purpose: a client whose access token has
    already expired must still be able to end its session.
    """
    revoke_one(db, payload.refresh_token)

    return None


# A resized 256px avatar is well under this; the cap stops the column being
# used as free file storage.
MAX_AVATAR_BYTES = 512 * 1024

ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}


@app.post("/auth/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replaces the caller's avatar.

    The bytes are stored in Postgres because the alternative is a storage
    service and its credentials for one small image per user.
    """
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Avatar must be a PNG, JPEG or WebP image",
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Avatar file is empty",
        )

    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar must be under 512 KB",
        )

    current_user.avatar_mime = file.content_type
    current_user.avatar_data = data

    db.commit()
    db.refresh(current_user)

    return UserOut.from_user(current_user)


@app.get("/auth/me/avatar")
def read_avatar(
    current_user: User = Depends(get_current_user),
):
    """Serves the caller's avatar bytes.

    Behind the same Bearer token as everything else, so an avatar URL cannot be
    walked by id.
    """
    if current_user.avatar_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No avatar set",
        )

    return Response(
        content=current_user.avatar_data,
        media_type=current_user.avatar_mime or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )


@app.delete("/auth/me/avatar", response_model=UserOut)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.avatar_mime = None
    current_user.avatar_data = None

    db.commit()
    db.refresh(current_user)

    return UserOut.from_user(current_user)
