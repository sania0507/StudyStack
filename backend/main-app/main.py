from fastapi import FastAPI, Depends, HTTPException
import uuid
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Base, Domain, Task #why did we import tasks? 
# Importing Task tells SQLAlchemy what the tasks table looks like, so Base.metadata.create_all() knows it needs to create/manage that table.
from schemas import (
    DomainCreate,
    DomainUpdate,
    DomainOut,
    TaskCreate,
    TaskOut,
    TaskUpdate
)




app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Domains
@app.post("/domains", response_model=DomainOut)
def create_domain(
    domain: DomainCreate,
    db: Session = Depends(get_db)
):
    new_domain = Domain(
        id=uuid.uuid4(),
        name=domain.name,
        colour="violet",
    )

    db.add(new_domain)
    db.commit()

    return new_domain


@app.get("/domains", response_model=list[DomainOut])
def get_domains(db: Session = Depends(get_db)):
    result = db.execute(select(Domain))
    return result.scalars().all()


@app.patch("/domains/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: uuid.UUID,
    domain: DomainUpdate,
    db: Session = Depends(get_db)
):
    existing_domain = db.get(Domain, domain_id)

    if existing_domain is None:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )

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
    db: Session = Depends(get_db)
):
    existing_domain = db.get(Domain, domain_id)

    if existing_domain is None:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )

    db.delete(existing_domain)
    db.commit()

    return {"message": "Domain deleted successfully"}

# Tasks
@app.post("/tasks", response_model=TaskOut)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
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

    return new_task

@app.get("/tasks", response_model=list[TaskOut])
def get_tasks(db: Session = Depends(get_db)):
    result = db.execute(select(Task))
    return result.scalars().all()

@app.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    task: TaskUpdate,
    db: Session = Depends(get_db)
):
    existing_task = db.get(Task, task_id)

    if existing_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if task.title is not None:
        existing_task.title = task.title

    if task.due_date is not None:
        existing_task.due_date = task.due_date

    if task.completed is not None:
        existing_task.completed = task.completed

        if task.completed:
            existing_task.completed_at = datetime.now()
        else:
            existing_task.completed_at = None

    db.commit()
    db.refresh(existing_task)

    return existing_task

@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    existing_task = db.get(Task, task_id)

    if existing_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    db.delete(existing_task)
    db.commit()

    return {"message": "Task deleted successfully"}