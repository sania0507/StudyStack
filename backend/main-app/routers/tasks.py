import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from events import publish_task_completed
from models import Domain, Task
from schemas import TaskCreate, TaskUpdate, TaskOut
from services.deadlines import is_overdue, task_to_out


router = APIRouter(prefix="/tasks", tags=["tasks"])


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

    return task_to_out(new_task)


@router.get("", response_model=list[TaskOut])
def get_tasks(
    completed: bool | None = None,
    overdue: bool | None = None,
    domain_id: uuid.UUID | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = (
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(Domain.user_id == user_id)
    )

    if completed is not None:
        query = query.where(Task.completed == completed)

    if domain_id is not None:
        query = query.where(Task.domain_id == domain_id)

    tasks = db.scalars(query).all()

    if overdue is not None:
        tasks = [
            task for task in tasks
            if is_overdue(task) == overdue
        ]

    return [task_to_out(task) for task in tasks]


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

    if task.due_date is not None:
        existing_task.due_date = task.due_date

    if task.completed is not None:
        existing_task.completed = task.completed
        existing_task.completed_at = (
            datetime.now() if task.completed else None
        )

    db.commit()
    db.refresh(existing_task)

    # Only announce the change when the task actually became completed.
    if task.completed is True:
        publish_task_completed(
            user_id=user_id,
            task_id=existing_task.id,
            domain_id=existing_task.domain_id,
        )

    return task_to_out(existing_task)


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
