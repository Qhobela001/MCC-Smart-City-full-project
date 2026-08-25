from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.alerts.models import (
    AlertSeverity,
    AlertType,
)


class AlertIncidentSummary(BaseModel):
    id: int
    incident_number: str
    title: str
    status: str
    priority: str

    model_config = ConfigDict(from_attributes=True)


class AlertRead(BaseModel):
    id: int
    recipient_user_id: int
    recipient_department_id: int | None
    incident_id: int | None

    alert_type: AlertType
    severity: AlertSeverity

    title: str
    message: str
    action_url: str | None

    is_read: bool
    read_at: datetime | None

    is_acknowledged: bool
    acknowledged_at: datetime | None

    is_archived: bool
    archived_at: datetime | None

    created_at: datetime
    incident: AlertIncidentSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: list[AlertRead]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class AlertActionResponse(BaseModel):
    success: bool = True
