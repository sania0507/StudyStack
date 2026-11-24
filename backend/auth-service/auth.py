from datetime import datetime, timedelta, timezone

import jwt
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from uuid import UUID
from database import get_db
from models import RefreshToken, User
from security import hash_refresh_token, new_refresh_token
from settings import settings


ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_MINUTES
    )

    payload = {
        "sub": user_id,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            raise unauthorized

    except jwt.InvalidTokenError:
        raise unauthorized from None

    try:
        parsed_user_id = UUID(user_id)
    except ValueError:
        raise unauthorized from None
    user = db.get(User, parsed_user_id)

    if user is None:
        raise unauthorized

    return user

# ---- refresh token issue, rotation and revocation --------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def issue_token_pair(
    db: Session,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    """Creates an access token plus a fresh refresh token.

    A new login starts a new family. A rotation continues the existing one, so
    that reuse anywhere in the chain can revoke exactly the right lineage.
    """
    raw_token = new_refresh_token()

    # Expired rows are dead weight: they can never authenticate anyone, and the
    # table would otherwise grow without bound. Pruning here keeps the cost on
    # the write path, where it is paid once per login or rotation.
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < _now(),
    ).delete(synchronize_session=False)

    record = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid.uuid4(),
        expires_at=_now() + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.add(record)
    db.commit()

    return create_access_token(str(user_id)), raw_token


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    """Kills every token descended from one login."""
    now = _now()

    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()


def revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    """Used when a password changes: every other session must end."""
    now = _now()

    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()


def revoke_one(db: Session, raw_token: str) -> bool:
    """Logout. Returns False for an unknown or already-revoked token."""
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )

    if record is None:
        return False

    # Idempotent: logging out twice is not an error.
    if record.revoked_at is None:
        record.revoked_at = _now()
        db.commit()

    return True


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[str, str]:
    """Exchanges a refresh token for a new pair, exactly once.

    The claim is a single conditional UPDATE. Reading the row and then
    revoking it would let two concurrent refreshes both pass the check and
    both issue new tokens, which silently breaks rotation.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )

    if record is None:
        raise invalid

    # A token that was already rotated has been presented twice. Either the
    # client or an attacker holds it, and one row cannot say which, so the
    # whole family dies and both parties are forced to log in again.
    if record.revoked_at is not None:
        revoke_family(db, record.family_id)
        raise invalid

    if record.expires_at <= _now():
        raise invalid

    replacement_id = uuid.uuid4()

    claimed = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == record.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), replaced_by_id=replacement_id)
    )

    if claimed.rowcount == 0:
        # Lost the race: another request rotated this token first.
        db.rollback()
        revoke_family(db, record.family_id)
        raise invalid

    db.commit()

    raw_token_new = new_refresh_token()

    db.add(
        RefreshToken(
            id=replacement_id,
            user_id=record.user_id,
            token_hash=hash_refresh_token(raw_token_new),
            family_id=record.family_id,
            expires_at=_now() + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    db.commit()

    return create_access_token(str(record.user_id)), raw_token_new
