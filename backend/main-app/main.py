from fastapi import FastAPI, Depends, HTTPException
import uuid
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal, get_db
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from auth import get_current_user_id
from models import Base, Domain, Task,Subtask #why did we import tasks? 
# Importing Task tells SQLAlchemy what the tasks table looks like, so Base.metadata.create_all() knows it needs to create/manage that table.
from schemas import (
    DomainCreate,
    DomainUpdate,
    DomainOut,
    TaskCreate,
    TaskUpdate,
    TaskOut,
    SubtaskCreate,
    SubtaskUpdate,
    SubtaskOut,
)




app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Base.metadata.create_all(bind=engine)


#DeadLine Logic
def is_overdue(task: Task) -> bool:

    return (
        task.due_date is not None
        and task.due_date < datetime.now()
        and not task.completed
    )
def task_to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        domain_id=task.domain_id,
        title=task.title,
        completed=task.completed,
        completed_at=task.completed_at,
        due_date=task.due_date,
        overdue=is_overdue(task),
    )

# Domains

@app.post("/domains", response_model=DomainOut)
def create_domain(
    domain: DomainCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    new_domain = Domain(
        id=uuid.uuid4(),
        name=domain.name,
        colour="violet",
        user_id=user_id,
    )

    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    return new_domain

@app.get("/domains", response_model=list[DomainOut])
def get_domains(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Domain).where(Domain.user_id == user_id)
    )
    return result.scalars().all()


@app.patch("/domains/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: uuid.UUID,
    domain: DomainUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    if domain.name is not None:
        existing_domain.name = domain.name

    if domain.colour is not None:
        existing_domain.colour = domain.colour

    db.commit()
    db.refresh(existing_domain)
    return existing_domain


@app.delete("/domains/{domain_id}")
def delete_domain(
    domain_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    db.delete(existing_domain)
    db.commit()

    return {"message": "Domain deleted successfully"}

# ----------------------


# Tasks
@app.post("/tasks", response_model=TaskOut)
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
@app.get("/tasks", response_model=list[TaskOut])
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
@app.patch("/tasks/{task_id}", response_model=TaskOut)
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

    return task_to_out(existing_task)


@app.delete("/tasks/{task_id}")
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

# Subtasks

@app.post("/subtasks", response_model=SubtaskOut)
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

@app.get("/subtasks", response_model=list[SubtaskOut])
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

@app.patch("/subtasks/{subtask_id}", response_model=SubtaskOut)
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


@app.delete("/subtasks/{subtask_id}")
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