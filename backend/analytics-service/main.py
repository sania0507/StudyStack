from datetime import date, timedelta
import uuid

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain, StudySession, Task
from settings import settings
from schemas import (
    AnalyticsSummary,
    DomainProgress,
    HeatmapDay,
    WeekdayMinutes,
)
from analytics import (
    current_streak,
    hours_per_week,
    minutes_by_day,
    overdue_task_count,
)

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


app = FastAPI(title="StudyStack Analytics Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def user_sessions(
    db: Session,
    user_id: uuid.UUID,
) -> list[StudySession]:
    return db.scalars(
        select(StudySession).where(StudySession.user_id == user_id)
    ).all()


def weekday_minutes(sessions: list[StudySession]) -> list[WeekdayMinutes]:
    totals = {name: 0 for name in WEEKDAY_NAMES}

    for session in sessions:
        name = WEEKDAY_NAMES[session.finished_at.weekday()]
        totals[name] += session.minutes

    return [
        WeekdayMinutes(weekday=name, minutes=totals[name])
        for name in WEEKDAY_NAMES
    ]


def domain_completion(
    db: Session,
    user_id: uuid.UUID,
) -> list[DomainProgress]:
    domains = db.scalars(
        select(Domain).where(Domain.user_id == user_id)
    ).all()

    progress = []

    for domain in domains:
        tasks = db.scalars(
            select(Task).where(Task.domain_id == domain.id)
        ).all()

        total = len(tasks)
        completed = len([task for task in tasks if task.completed])

        # Guard against dividing by zero for a domain with no tasks.
        percent = round((completed / total) * 100, 1) if total else 0.0

        progress.append(
            DomainProgress(
                domain_id=domain.id,
                name=domain.name,
                total_tasks=total,
                completed_tasks=completed,
                completion_percent=percent,
            )
        )

    return progress


def heatmap(
    sessions: list[StudySession],
    days: int = 30,
) -> list[HeatmapDay]:
    totals = minutes_by_day(sessions)
    today = date.today()

    result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        result.append(HeatmapDay(day=day, minutes=totals.get(day, 0)))

    return result


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    heatmap_days: int = Query(default=30, ge=1, le=365),
):
    sessions = user_sessions(db, user_id)

    total_minutes = sum(session.minutes for session in sessions)
    days_with_sessions = len(minutes_by_day(sessions))

    # Average minutes per day that actually has study activity.
    sessions_per_day = (
        round(total_minutes / days_with_sessions, 1)
        if days_with_sessions
        else 0.0
    )

    return AnalyticsSummary(
        hours_per_week=hours_per_week(sessions),
        streak=current_streak(sessions),
        overdue_count=overdue_task_count(db, user_id),
        total_minutes=total_minutes,
        total_sessions=len(sessions),
        days_with_sessions=days_with_sessions,
        sessions_per_day=sessions_per_day,
        weekday_minutes=weekday_minutes(sessions),
        domain_completion=domain_completion(db, user_id),
        heatmap=heatmap(sessions, heatmap_days),
    )
