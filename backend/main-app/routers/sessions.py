import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain, StudySession, Task
from schemas import StudySessionCreate, StudySessionOut


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=StudySessionOut)
def create_study_session(
    session: StudySessionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == session.domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    # If a task was named, prove it is the caller's and lives in that domain.
    if session.task_id is not None:
        owned_task = db.scalar(
            select(Task).where(
                Task.id == session.task_id,
                Task.domain_id == session.domain_id,
            )
        )

        if owned_task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    new_session = StudySession(
        id=uuid.uuid4(),
        user_id=user_id,
        domain_id=session.domain_id,
        task_id=session.task_id,
        duration_seconds=session.duration_seconds,
        finished_at=datetime.now(),
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.get("", response_model=list[StudySessionOut])
def get_study_sessions(
    domain_id: uuid.UUID | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = select(StudySession).where(StudySession.user_id == user_id)

    if domain_id is not None:
        query = query.where(StudySession.domain_id == domain_id)

    return db.scalars(query).all()
