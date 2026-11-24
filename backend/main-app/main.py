from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import Base, Subtask, Task, Reminder, StudySession
# Importing the models tells SQLAlchemy what each table looks like, so
# Base.metadata.create_all() knows what to create/manage.
from reminders import start_scheduler, stop_scheduler
from routers import (
    analytics as analytics_router,
    domains as domains_router,
    notes as notes_router,
    reminders as reminders_router,
    sessions as sessions_router,
    subtasks as subtasks_router,
    tasks as tasks_router,
    vision as vision_router,
)
from settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The reminder worker runs for as long as the application is alive.
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="StudyStack Task Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(domains_router.router)
app.include_router(tasks_router.router)
app.include_router(subtasks_router.router)
app.include_router(reminders_router.router)
app.include_router(sessions_router.router)
app.include_router(analytics_router.router)
app.include_router(vision_router.router)
app.include_router(notes_router.router)
