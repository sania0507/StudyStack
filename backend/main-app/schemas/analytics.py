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
    completion_percent: float


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
    domain_completion: list[DomainProgress]
    heatmap: list[HeatmapDay]
