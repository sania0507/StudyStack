import math
from datetime import date, datetime, time, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Domain, StudySession, Subtask, Task, TaskCompletion


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


# Days on which the user did anything at all: a timer session, or a task
# ticked. Ticking a task is work, even with no timer running, so a streak that
# read only sessions reported 0 for someone who had done nothing but finish
# tasks all week.
def active_days(
    sessions: list[StudySession],
    completions: dict[date, int] | None = None,
) -> set[date]:
    days = set(seconds_by_day(sessions))

    if completions:
        days |= {day for day, count in completions.items() if count}

    return days


# Counts consecutive days that ended with at least one session or completion.
def current_streak(
    sessions: list[StudySession],
    today: date | None = None,
    completions: dict[date, int] | None = None,
) -> int:
    today = today or date.today()

    days = active_days(sessions, completions)

    if not days:
        return 0

    # A streak may start yesterday, so studying today is not required for a
    # streak that is still alive.
    cursor = today
    if cursor not in days:
        cursor = today - timedelta(days=1)

    streak = 0
    while cursor in days:
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


def task_progress(task: Task, subtask_total: int, subtask_done: int) -> bool:
    """Was this task finished?

    Hybrid rule, because a task can be tracked either way:
    - with subtasks: done only when every subtask is ticked, so "5 topics, 4
      done" is not a finished subject;
    - without subtasks: fall back to the task's own tick, so a plain to-do is
      not stuck at 0% forever.
    """
    if subtask_total:
        return subtask_done >= subtask_total

    return bool(task.completed)


def domain_completion(db: Session, user_id: uuid.UUID) -> list[dict]:
    """Per-domain progress, counted in subtasks where they exist.

    Domains are loaded with their tasks and subtasks in three queries rather
    than one per domain, so this stays flat as the account grows.
    """
    domains = db.scalars(
        select(Domain).where(Domain.user_id == user_id)
    ).all()

    # No domains means no ids to filter on; `IN ()` is not valid SQL, so return
    # before building the queries.
    if not domains:
        return []

    tasks_by_domain: dict[uuid.UUID, list[Task]] = {}

    for task in db.scalars(
        select(Task).where(Task.domain_id.in_([domain.id for domain in domains]))
    ):
        tasks_by_domain.setdefault(task.domain_id, []).append(task)

    all_task_ids = [task.id for tasks in tasks_by_domain.values() for task in tasks]

    subtasks_by_task: dict[uuid.UUID, list[Subtask]] = {}

    if all_task_ids:
        for subtask in db.scalars(
            select(Subtask).where(Subtask.task_id.in_(all_task_ids))
        ):
            subtasks_by_task.setdefault(subtask.task_id, []).append(subtask)

    progress = []

    for domain in domains:
        tasks = tasks_by_domain.get(domain.id, [])

        total_tasks = len(tasks)
        completed_tasks = 0
        total_subtasks = 0
        completed_subtasks = 0

        for task in tasks:
            subtasks = subtasks_by_task.get(task.id, [])
            done = len([s for s in subtasks if s.completed])

            total_subtasks += len(subtasks)
            completed_subtasks += done

            if task_progress(task, len(subtasks), done):
                completed_tasks += 1

        # Progress is measured in subtasks when the domain has any, because
        # that is the finer unit — finishing 4 of 5 topics is 80%, not 0% or
        # 100%. A domain with no subtasks at all falls back to its tasks, so a
        # plain to-do list still moves.
        if total_subtasks:
            percent = round((completed_subtasks / total_subtasks) * 100, 1)
        elif total_tasks:
            percent = round((completed_tasks / total_tasks) * 100, 1)
        else:
            percent = 0.0

        progress.append(
            {
                "domain_id": domain.id,
                "name": domain.name,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "total_subtasks": total_subtasks,
                "completed_subtasks": completed_subtasks,
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
    #
    # The flag source joins through domains, so deleting a domain drops the
    # tasks that still carry a flag. The log source is scoped by its own
    # user_id, so it survives the delete: that is where the history lives once
    # a domain is gone.
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
            .where(TaskCompletion.user_id == user_id)
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
