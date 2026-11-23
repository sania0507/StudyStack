from datetime import date, datetime, time, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Domain, StudySession, Task


# Turns raw session rows into {date: minutes}.
def minutes_by_day(
    sessions: list[StudySession],
) -> dict[date, int]:
    totals: dict[date, int] = {}

    for session in sessions:
        day = session.finished_at.date()
        totals[day] = totals.get(day, 0) + session.minutes

    return totals


# Counts consecutive days that ended with at least one session.
def current_streak(sessions: list[StudySession], today: date | None = None) -> int:
    today = today or date.today()

    totals = minutes_by_day(sessions)

    if not totals:
        return 0

    # A streak is allowed to start yesterday, so studying today is not
    # required for a streak that is still alive.
    cursor = today
    if cursor not in totals:
        cursor = today - timedelta(days=1)

    streak = 0
    while cursor in totals:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def week_bounds(today: date | None = None) -> tuple[datetime, datetime]:
    today = today or date.today()

    start_of_week = today - timedelta(days=today.weekday())

    start = datetime.combine(start_of_week, time.min)
    end = start + timedelta(days=7)

    return start, end


def hours_per_week(
    sessions: list[StudySession],
    today: date | None = None,
) -> float:
    start, end = week_bounds(today)

    total_minutes = sum(
        session.minutes
        for session in sessions
        if start <= session.finished_at < end
    )

    # Rounding keeps the JSON readable instead of 1.6666666666.
    return round(total_minutes / 60, 2)


def overdue_task_count(db: Session, user_id: uuid.UUID) -> int:
    # Overdue is derived, never stored: an incomplete task whose due_date
    # has already passed.
    count = db.scalar(
        select(func.count())
        .select_from(Task)
        .join(Domain, Task.domain_id == Domain.id)
        .where(
            Domain.user_id == user_id,
            Task.completed.is_(False),
            Task.due_date.is_not(None),
            Task.due_date < datetime.now(),
        )
    )

    return count or 0
