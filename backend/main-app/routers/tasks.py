import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain, Reminder, Task
from schemas import TaskCreate, TaskUpdate, TaskOut
from services.deadlines import is_overdue, task_to_out
from services.recurrence import record_completion, reset_recurring_tasks


router = APIRouter(prefix="/tasks", tags=["tasks"])


# The soonest still-pending reminder for each task, in one query rather
# than one query per task.
def pending_reminder_times(
    db: Session,
    task_ids: list[uuid.UUID],
) -> dict[uuid.UUID, datetime]:
    if not task_ids:
        return {}

    rows = db.execute(
        select(Reminder.task_id, func.min(Reminder.remind_at))
        .where(
            Reminder.task_id.in_(task_ids),
            Reminder.sent_at.is_(None),
        )
        .group_by(Reminder.task_id)
    ).all()

    return {task_id: remind_at for task_id, remind_at in rows}


def reminder_time_for(db: Session, task_id: uuid.UUID) -> datetime | None:
    return pending_reminder_times(db, [task_id]).get(task_id)


@router.post("", response_model=TaskOut)
def create_task(
    task: TaskCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == task.domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    new_task = Task(
        id=uuid.uuid4(),
        domain_id=task.domain_id,
        title=task.title,
        completed=False,
        completed_at=None,
        due_date=task.due_date,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return task_to_out(new_task, reminder_time_for(db, new_task.id))


@router.get("", response_model=list[TaskOut])
def get_tasks(
    completed: bool | None = None,
    overdue: bool | None = None,
    domain_id: uuid.UUID | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Cheap, idempotent, and it means the dashboard never needs a scheduler to
    # be correct: opening the list on a new day resets yesterday's routine.
    reset_recurring_tasks(db, user_id)

    query = (
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(Domain.user_id == user_id)
    )

    if completed is not None:
        query = query.where(Task.completed == completed)

    if domain_id is not None:
        query = query.where(Task.domain_id == domain_id)

    # Overdue is derived, so it still cannot be indexed, but it can be
    # expressed as a predicate: the database does the filtering instead of
    # shipping every row to Python first.
    if overdue is not None:
        is_past_due = Task.due_date.is_not(None) & (Task.due_date < datetime.now())

        if overdue:
            query = query.where(is_past_due, Task.completed.is_(False))
        else:
            query = query.where(
                Task.due_date.is_(None)
                | (Task.due_date >= datetime.now())
                | Task.completed.is_(True)
            )

    tasks = db.scalars(query).all()

    reminder_times = pending_reminder_times(db, [task.id for task in tasks])

    return [
        task_to_out(task, reminder_times.get(task.id))
        for task in tasks
    ]


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    task: TaskUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_task = db.scalar(
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Task.id == task_id,
            Domain.user_id == user_id,
        )
    )

    if existing_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.title is not None:
        existing_task.title = task.title

    # Absent leaves the deadline alone; an explicit null clears it. Testing
    # for None alone would make it impossible to remove a due date.
    if "due_date" in task.model_fields_set:
        existing_task.due_date = task.due_date

    if task.completed is not None:
        existing_task.completed = task.completed
        existing_task.completed_at = (
            datetime.now() if task.completed else None
        )

        # Log the day it was finished. For recurring tasks the tick is cleared
        # tomorrow, so this row is the only lasting record.
        if task.completed:
            record_completion(db, existing_task)

    db.commit()
    db.refresh(existing_task)

    return task_to_out(existing_task, reminder_time_for(db, existing_task.id))


@router.delete("/{task_id}")
def delete_task(
    task_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_task = db.scalar(
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Task.id == task_id,
            Domain.user_id == user_id,
        )
    )

    if existing_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(existing_task)
    db.commit()

    return {"message": "Task deleted successfully"}
