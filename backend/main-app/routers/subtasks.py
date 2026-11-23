import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain, Subtask, Task
from schemas import SubtaskCreate, SubtaskUpdate, SubtaskOut


router = APIRouter(prefix="/subtasks", tags=["subtasks"])


@router.post("", response_model=SubtaskOut)
def create_subtask(
    subtask: SubtaskCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_task = db.scalar(
        select(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Task.id == subtask.task_id,
            Domain.user_id == user_id,
        )
    )

    if existing_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    new_subtask = Subtask(
        id=uuid.uuid4(),
        task_id=subtask.task_id,
        title=subtask.title,
        completed=False,
    )

    db.add(new_subtask)
    db.commit()
    db.refresh(new_subtask)

    return new_subtask


@router.get("", response_model=list[SubtaskOut])
def get_subtasks(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = (
        select(Subtask)
        .join(Task, Subtask.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(Domain.user_id == user_id)
    )

    return db.scalars(query).all()


@router.patch("/{subtask_id}", response_model=SubtaskOut)
def update_subtask(
    subtask_id: uuid.UUID,
    subtask: SubtaskUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_subtask = db.scalar(
        select(Subtask)
        .join(Task, Subtask.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Subtask.id == subtask_id,
            Domain.user_id == user_id,
        )
    )

    if existing_subtask is None:
        raise HTTPException(status_code=404, detail="Subtask not found")

    if subtask.title is not None:
        existing_subtask.title = subtask.title

    if subtask.completed is not None:
        existing_subtask.completed = subtask.completed

    db.commit()
    db.refresh(existing_subtask)

    return existing_subtask


@router.delete("/{subtask_id}")
def delete_subtask(
    subtask_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_subtask = db.scalar(
        select(Subtask)
        .join(Task, Subtask.task_id == Task.id)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Subtask.id == subtask_id,
            Domain.user_id == user_id,
        )
    )

    if existing_subtask is None:
        raise HTTPException(status_code=404, detail="Subtask not found")

    db.delete(existing_subtask)
    db.commit()

    return {"message": "Subtask deleted successfully"}
