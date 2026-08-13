from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.alerts.schemas import AlertRead
from app.modules.dashboard import repository
from app.modules.dashboard.schemas import (
    DashboardStats,
    DashboardSummaryResponse,
)
from app.modules.incidents import service as incident_service
from app.modules.incidents.models import IncidentStatus
from app.modules.users.models import User


OPEN_STATUSES = (
    IncidentStatus.new,
    IncidentStatus.under_review,
    IncidentStatus.confirmed,
    IncidentStatus.assigned,
    IncidentStatus.in_progress,
)


def get_summary(
        db: Session,
        actor: User,
) -> DashboardSummaryResponse:
    status_counts = (
        repository.incident_status_counts(
            db,
            actor,
        )
    )

    open_incidents = sum(
        status_counts.get(status, 0)
        for status in OPEN_STATUSES
    )

    critical_incidents = (
        repository.critical_incident_count(
            db,
            actor,
        )
    )

    resolved_incidents = (
        status_counts.get(
            IncidentStatus.resolved,
            0,
        )
    )

    unread_alerts = (
        repository.unread_alert_count(
            db,
            actor.id,
        )
    )

    incidents = repository.recent_incidents(
        db,
        actor,
        limit=8,
    )

    alerts = repository.recent_alerts(
        db,
        actor.id,
        limit=6,
    )

    complete_status_counts = {
        status.value: status_counts.get(
            status,
            0,
        )
        for status in IncidentStatus
    }

    return DashboardSummaryResponse(
        stats=DashboardStats(
            open_incidents=open_incidents,
            critical_incidents=critical_incidents,
            resolved_incidents=resolved_incidents,
            unread_alerts=unread_alerts,
        ),
        status_counts=complete_status_counts,
        recent_incidents=[
            incident_service.to_read(
                incident
            )
            for incident in incidents
        ],
        recent_alerts=[
            AlertRead.model_validate(
                alert
            )
            for alert in alerts
        ],
        generated_at=datetime.now(
            timezone.utc
        ),
    )