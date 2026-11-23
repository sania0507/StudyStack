import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain, Reminder, Task
from schemas import ReminderCreate, ReminderUpdate, ReminderOut


router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderOut)
def create_reminder(
    reminder: ReminderCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_task = db.scalar(
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Task.id == reminder.task_id,
            Domain.user_id == user_id,
        )
    )

    if existing_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    new_reminder = Reminder(
        id=uuid.uuid4(),
        task_id=reminder.task_id,
        remind_at=reminder.remind_at,
        sent_at=None,
    )

    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)

    return new_reminder


@router.get("", response_model=list[ReminderOut])
def get_reminders(
    task_id: uuid.UUID | None = None,
    sent: bool | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = (
        select(Reminder)
        .join(Task, Reminder.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(Domain.user_id == user_id)
    )

    if task_id is not None:
        query = query.where(Reminder.task_id == task_id)

    if sent is True:
        query = query.where(Reminder.sent_at.is_not(None))

    if sent is False:
        query = query.where(Reminder.sent_at.is_(None))

    return db.scalars(query).all()


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: uuid.UUID,
    reminder: ReminderUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_reminder = db.scalar(
        select(Reminder)
        .join(Task, Reminder.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Reminder.id == reminder_id,
            Domain.user_id == user_id,
        )
    )

    if existing_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.remind_at is not None:
        existing_reminder.remind_at = reminder.remind_at

        # Moving the reminder to a new time makes it pending again.
        existing_reminder.sent_at = None

    db.commit()
    db.refresh(existing_reminder)

    return existing_reminder


@router.delete("/{reminder_id}")
def delete_reminder(
    reminder_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_reminder = db.scalar(
        select(Reminder)
        .join(Task, Reminder.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Reminder.id == reminder_id,
            Domain.user_id == user_id,
        )
    )

    if existing_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(existing_reminder)
    db.commit()

    return {"message": "Reminder deleted successfully"}
