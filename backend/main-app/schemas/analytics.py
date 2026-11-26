import uuid
from datetime import date

from pydantic import BaseModel


class WeekdayMinutes(BaseModel):
    weekday: str
    minutes: int


class DomainProgress(BaseModel):
    domain_id: uuid.UUID
    name: str
    total_tasks: int
    completed_tasks: int
    # Tracked at subtask granularity because that is the unit people actually
    # tick off ("LR0, SLR, CLR"). completion_percent measures subtasks when the
    # domain has any, and falls back to tasks when it has none.
    total_subtasks: int = 0
    completed_subtasks: int = 0
    completion_percent: float


class TaskTimeTotal(BaseModel):
    """Focus time recorded against one task."""

    task_id: uuid.UUID
    seconds: int


class HeatmapDay(BaseModel):
    day: date
    minutes: int
    # Tasks finished that day. A day with effort but no timer session still
    # counts as showing up, so the heatmap needs both numbers.
    tasks_completed: int


class AnalyticsSummary(BaseModel):
    # Required by the roadmap.
    hours_per_week: float
    streak: int
    overdue_count: int

    # Extra StudyStack statistics.
    total_minutes: int
    total_sessions: int
    days_with_sessions: int
    sessions_per_day: float
    weekday_minutes: list[WeekdayMinutes]
    # Per-task focus time, so a task row can show "2h 14m recorded".
    task_totals: list[TaskTimeTotal]
    domain_completion: list[DomainProgress]
    heatmap: list[HeatmapDay]
