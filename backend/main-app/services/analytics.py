import math
from datetime import date, datetime, time, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Domain, StudySession, Task, TaskCompletion


# Analytics lives inside the task service because it only ever reads tables
# this service owns. That keeps it free to host (one service instead of two)
# and removes the need for a message broker.

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# Turns raw session rows into {date: seconds}.
def seconds_by_day(
    sessions: list[StudySession],
) -> dict[date, int]:
    totals: dict[date, int] = {}

    for session in sessions:
        day = session.finished_at.date()
        totals[day] = totals.get(day, 0) + session.duration_seconds

    return totals


# Counts consecutive days that ended with at least one session.
def current_streak(
    sessions: list[StudySession],
    today: date | None = None,
) -> int:
    today = today or date.today()

    totals = seconds_by_day(sessions)

    if not totals:
        return 0

    # A streak may start yesterday, so studying today is not required for a
    # streak that is still alive.
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

    total_seconds = sum(
        session.duration_seconds
        for session in sessions
        if start <= session.finished_at < end
    )

    # Rounding keeps the JSON readable instead of 1.6666666666.
    return round(total_seconds / 3600, 2)


def seconds_per_task(
    sessions: list[StudySession],
) -> dict[uuid.UUID, int]:
    """Total focus time per task, for the "how long did this take" view."""
    totals: dict[uuid.UUID, int] = {}

    for session in sessions:
        if session.task_id is None:
            continue

        totals[session.task_id] = totals.get(session.task_id, 0) + session.duration_seconds

    return totals


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


def weekday_minutes(sessions: list[StudySession]) -> list[dict]:
    """Focus time per weekday, in whole minutes (the chart's unit)."""
    totals = {name: 0 for name in WEEKDAY_NAMES}

    for session in sessions:
        name = WEEKDAY_NAMES[session.finished_at.weekday()]
        totals[name] += session.duration_seconds

    return [
        {"weekday": name, "minutes": round(totals[name] / 60)}
        for name in WEEKDAY_NAMES
    ]


def domain_completion(db: Session, user_id: uuid.UUID) -> list[dict]:
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
            {
                "domain_id": domain.id,
                "name": domain.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_percent": percent,
            }
        )

    return progress


def tasks_completed_by_day(db: Session, user_id: uuid.UUID) -> dict[date, int]:
    """How many tasks the user finished on each day.

    completed_at is the only record of *when* a task was finished, so this is
    the one source for historical completions. Grouping in SQL keeps it to a
    single query regardless of task count.
    """
    # Two sources, because a completion can be recorded either way: the flag on
    # a task that is still ticked, and the log for tasks that have since been
    # reset by a recurring domain. Taking the larger per day avoids
    # double-counting a task that is both ticked now and logged today.
    from_flag = dict(
        db.execute(
            select(func.date(Task.completed_at), func.count())
            .select_from(Task)
            .join(Domain, Task.domain_id == Domain.id)
            .where(
                Domain.user_id == user_id,
                Task.completed_at.is_not(None),
            )
            .group_by(func.date(Task.completed_at))
        ).all()
    )

    from_log = dict(
        db.execute(
            select(TaskCompletion.completed_on, func.count())
            .select_from(TaskCompletion)
            .join(Task, TaskCompletion.task_id == Task.id)
            .join(Domain, Task.domain_id == Domain.id)
            .where(Domain.user_id == user_id)
            .group_by(TaskCompletion.completed_on)
        ).all()
    )

    days = set(from_flag) | set(from_log)
    return {day: max(from_flag.get(day, 0), from_log.get(day, 0)) for day in days}


def heatmap(
    sessions: list[StudySession],
    days: int = 30,
    completions: dict[date, int] | None = None,
) -> list[dict]:
    totals = seconds_by_day(sessions)
    completions = completions or {}
    today = date.today()

    result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        result.append(
            {
                "day": day,
                # The heatmap reads minutes for its levels; rounding up means a
                # 40-second block still counts as a minute rather than zero.
                "minutes": math.ceil(totals.get(day, 0) / 60),
                "tasks_completed": completions.get(day, 0),
            }
        )

    return result
