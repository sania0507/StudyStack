import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import StudySession
from schemas.analytics import AnalyticsSummary
from services.analytics import (
    current_streak,
    domain_completion,
    heatmap,
    hours_per_week,
    minutes_by_day,
    overdue_task_count,
    tasks_completed_by_day,
    weekday_minutes,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


# Kept in the task service rather than a separate one: every number here is
# derived from tables this service already owns, so splitting it out cost a
# whole extra deployment (and a message broker) for no benefit.
@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    heatmap_days: int = Query(default=30, ge=1, le=365),
):
    sessions = db.scalars(
        select(StudySession).where(StudySession.user_id == user_id)
    ).all()

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
        heatmap=heatmap(
            sessions,
            heatmap_days,
            tasks_completed_by_day(db, user_id),
        ),
    )
