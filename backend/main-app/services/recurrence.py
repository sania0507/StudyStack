"""Daily routines: resetting recurring tasks without losing their history.

A recurring domain's tasks are things done again every day. The `completed`
column still holds today's state, so the dashboard reads exactly as before, and
`task_completions` holds every day a task was finished so nothing is lost when
the tick is cleared.
"""

from datetime import date, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models import Domain, Task, TaskCompletion


def reset_recurring_tasks(db: Session, user_id, today: date | None = None) -> int:
    """Un-ticks tasks in recurring domains that were completed before today.

    Completed today is left alone, so a user who ticks a prayer at 06:00 does
    not lose it if they reload the page in the afternoon. Returns how many rows
    were reset, which makes it testable without a scheduler.
    """
    today = today or date.today()
    start_of_today = datetime.combine(today, datetime.min.time())

    recurring_domain_ids = select(Domain.id).where(
        Domain.user_id == user_id,
        Domain.repeats_daily.is_(True),
    )

    result = db.execute(
        update(Task)
        .where(
            Task.domain_id.in_(recurring_domain_ids),
            Task.completed.is_(True),
            Task.completed_at.is_not(None),
            Task.completed_at < start_of_today,
        )
        .values(completed=False, completed_at=None)
        .execution_options(synchronize_session=False)
    )

    db.commit()

    return result.rowcount or 0


def record_completion(db: Session, task: Task, today: date | None = None) -> None:
    """Logs that a task was finished today. Safe to call twice."""
    today = today or date.today()

    exists = db.scalar(
        select(TaskCompletion).where(
            TaskCompletion.task_id == task.id,
            TaskCompletion.completed_on == today,
        )
    )

    if exists is not None:
        return

    db.add(
        TaskCompletion(
            id=__import__("uuid").uuid4(),
            task_id=task.id,
            completed_on=today,
        )
    )
