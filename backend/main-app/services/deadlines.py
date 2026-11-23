from datetime import datetime

from models import Task
from schemas import TaskOut


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
