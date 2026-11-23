from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Reminder, Task


# Checks every reminder that is due and not yet sent.
# Returns how many reminders this run marked as sent, which makes it
# easy to test the worker without starting the scheduler.
def send_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now()

    due_reminders = db.scalars(
        select(Reminder)
        .where(
            Reminder.remind_at <= now,
            Reminder.sent_at.is_(None),
        )
    ).all()

    sent_count = 0

    for reminder in due_reminders:
        task = db.get(Task, reminder.task_id)

        # A reminder for a task that no longer exists is stale, so mark it
        # as handled instead of leaving it in the queue forever.
        if task is None:
            reminder.sent_at = now
            continue

        if task.completed:
            reminder.sent_at = now
            continue

        # Printing stands in for the notification channel. Swapping this for
        # email or push later does not change the reminder bookkeeping.
        print(f"[reminder] Task due soon: {task.title}")

        reminder.sent_at = now
        sent_count += 1

    db.commit()

    return sent_count


def send_due_reminders_job() -> None:
    # The scheduler needs its own session because it runs outside a request.
    db = SessionLocal()
    try:
        send_due_reminders(db)
    finally:
        db.close()


scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if scheduler.running:
        return

    # max_instances=1 stops a slow run from overlapping with the next tick.
    scheduler.add_job(
        send_due_reminders_job,
        trigger="interval",
        seconds=60,
        id="send_due_reminders",
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
