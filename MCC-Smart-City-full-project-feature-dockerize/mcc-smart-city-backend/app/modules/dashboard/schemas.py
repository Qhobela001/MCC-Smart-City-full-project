from datetime import datetime

from pydantic import BaseModel

from app.modules.alerts.schemas import AlertRead
from app.modules.incidents.schemas import IncidentRead


class DashboardStats(BaseModel):
    open_incidents: int
    critical_incidents: int
    resolved_incidents: int
    unread_alerts: int


class DashboardSummaryResponse(BaseModel):
    stats: DashboardStats
    status_counts: dict[str, int]
    recent_incidents: list[IncidentRead]
    recent_alerts: list[AlertRead]
    generated_at: datetime
