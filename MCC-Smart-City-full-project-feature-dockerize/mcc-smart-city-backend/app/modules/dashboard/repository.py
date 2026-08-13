from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.alerts import repository as alert_repository
from app.modules.alerts.models import Alert
from app.modules.incidents.models import (
    Incident,
    IncidentPriority,
    IncidentStatus,
)
from app.modules.incidents.repository import (
    visible_incident_filter,
)
from app.modules.users.models import User


def incident_status_counts(
        db: Session,
        actor: User,
) -> dict[IncidentStatus, int]:
    """
    Return exact incident counts by status while preserving
    the same visibility rules used by the Incidents module.
    """

    statement = (
        select(
            Incident.status,
            func.count(Incident.id),
        )
        .where(
            visible_incident_filter(actor)
        )
        .group_by(Incident.status)
    )

    rows = db.execute(statement).all()

    return {
        status: int(total)
        for status, total in rows
    }


def critical_incident_count(
        db: Session,
        actor: User,
) -> int:
    """
    Count critical incidents visible to this user.

    This preserves the behaviour of the existing dashboard,
    which counted all visible critical incidents regardless
    of status.
    """

    statement = (
        select(
            func.count(Incident.id)
        )
        .where(
            visible_incident_filter(actor),
            Incident.priority
            == IncidentPriority.critical,
            )
    )

    return int(
        db.scalar(statement)
        or 0
    )


def recent_incidents(
        db: Session,
        actor: User,
        *,
        limit: int = 8,
) -> list[Incident]:
    statement = (
        select(Incident)
        .where(
            visible_incident_filter(actor)
        )
        .order_by(
            Incident.created_at.desc(),
            Incident.id.desc(),
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement)
        .unique()
        .all()
    )


def recent_alerts(
        db: Session,
        user_id: int,
        *,
        limit: int = 6,
) -> list[Alert]:
    items, _ = alert_repository.list_for_user(
        db,
        user_id,
        limit=limit,
        offset=0,
        unread_only=False,
        include_archived=False,
    )

    return items


def unread_alert_count(
        db: Session,
        user_id: int,
) -> int:
    return alert_repository.unread_count(
        db,
        user_id,
    )