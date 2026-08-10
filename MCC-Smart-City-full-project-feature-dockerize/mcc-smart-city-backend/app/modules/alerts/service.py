from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.deps import user_has_permission
from app.modules.alerts import repository
from app.modules.alerts.models import (
    Alert,
    AlertSeverity,
    AlertType,
)
from app.modules.incidents.models import (
    Incident,
    IncidentPriority,
    IncidentStatus,
)
from app.modules.users.models import User


def severity_from_incident(
    incident: Incident,
) -> AlertSeverity:
    mapping = {
        IncidentPriority.low: AlertSeverity.low,
        IncidentPriority.medium: AlertSeverity.medium,
        IncidentPriority.high: AlertSeverity.high,
        IncidentPriority.critical: AlertSeverity.critical,
    }
    return mapping.get(
        incident.priority,
        AlertSeverity.info,
    )


def _unique_users(
    users: Iterable[User],
    *,
    exclude_user_ids: set[int] | None = None,
) -> list[User]:
    excluded = exclude_user_ids or set()
    seen: set[int] = set()
    result: list[User] = []

    for user in users:
        if user.id in excluded or user.id in seen:
            continue

        if not user.is_active:
            continue

        seen.add(user.id)
        result.append(user)

    return result


def _create_for_users(
    db: Session,
    recipients: Iterable[User],
    *,
    incident: Incident | None,
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    message: str,
    action_url: str | None,
    recipient_department_id: int | None = None,
    exclude_user_ids: set[int] | None = None,
) -> list[Alert]:
    created: list[Alert] = []

    for user in _unique_users(
        recipients,
        exclude_user_ids=exclude_user_ids,
    ):
        alert = Alert(
            recipient_user_id=user.id,
            recipient_department_id=(
                recipient_department_id
                if recipient_department_id is not None
                else user.department_id
            ),
            incident_id=incident.id if incident else None,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            action_url=action_url,
        )
        repository.create(db, alert)
        created.append(alert)

    return created


def _department_operational_recipients(
    db: Session,
    department_id: int | None,
) -> list[User]:
    if department_id is None:
        return []

    users = repository.active_department_users(
        db,
        department_id,
    )

    # Only users already authorised to participate in
    # incident operations receive department-wide alerts.
    return [
        user
        for user in users
        if (
            user_has_permission(user, "incidents.view")
            or user_has_permission(user, "incidents.assign")
            or user_has_permission(user, "incidents.resolve")
        )
    ]


def notify_incident_created(
    db: Session,
    *,
    incident: Incident,
    actor: User,
) -> list[Alert]:
    recipients: list[User] = []

    if incident.assigned_user is not None:
        recipients.append(incident.assigned_user)
    else:
        recipients.extend(
            _department_operational_recipients(
                db,
                incident.department_id,
            )
        )

    # Critical incidents are also surfaced to SuperAdmins.
    if incident.priority == IncidentPriority.critical:
        recipients.extend(
            repository.active_superadmins(db)
        )

    return _create_for_users(
        db,
        recipients,
        incident=incident,
        alert_type=AlertType.incident_created,
        severity=severity_from_incident(incident),
        title=f"New incident: {incident.title}",
        message=(
            f"{incident.incident_number} was reported"
            + (
                f" at {incident.location_name}."
                if incident.location_name
                else "."
            )
        ),
        action_url=f"/incidents?incident={incident.id}",
        recipient_department_id=incident.department_id,
        exclude_user_ids={actor.id},
    )


def notify_incident_assigned(
    db: Session,
    *,
    incident: Incident,
    actor: User,
) -> list[Alert]:
    recipients: list[User] = []

    if incident.assigned_user is not None:
        recipients.append(incident.assigned_user)

    # The incident creator is also informed if someone else
    # performed the assignment.
    if incident.created_by is not None:
        recipients.append(incident.created_by)

    return _create_for_users(
        db,
        recipients,
        incident=incident,
        alert_type=AlertType.incident_assigned,
        severity=severity_from_incident(incident),
        title=f"Incident assigned: {incident.incident_number}",
        message=(
            f"{incident.title} has been assigned to "
            f"{incident.assigned_user.full_name if incident.assigned_user else 'an officer'}."
        ),
        action_url=f"/incidents?incident={incident.id}",
        recipient_department_id=incident.department_id,
        exclude_user_ids={actor.id},
    )


def notify_status_changed(
    db: Session,
    *,
    incident: Incident,
    actor: User,
    previous_status: IncidentStatus,
) -> list[Alert]:
    recipients: list[User] = []

    if incident.created_by is not None:
        recipients.append(incident.created_by)

    if incident.assigned_user is not None:
        recipients.append(incident.assigned_user)

    alert_type = (
        AlertType.incident_resolved
        if incident.status == IncidentStatus.resolved
        else AlertType.incident_status_changed
    )

    severity = (
        AlertSeverity.info
        if incident.status == IncidentStatus.resolved
        else severity_from_incident(incident)
    )

    return _create_for_users(
        db,
        recipients,
        incident=incident,
        alert_type=alert_type,
        severity=severity,
        title=f"Incident status: {incident.incident_number}",
        message=(
            f"{incident.title} changed from "
            f"{previous_status.value.replace('_', ' ')} to "
            f"{incident.status.value.replace('_', ' ')}."
        ),
        action_url=f"/incidents?incident={incident.id}",
        recipient_department_id=incident.department_id,
        exclude_user_ids={actor.id},
    )


def notify_evidence_uploaded(
    db: Session,
    *,
    incident: Incident,
    actor: User,
    original_file_name: str,
) -> list[Alert]:
    recipients: list[User] = []

    if incident.created_by is not None:
        recipients.append(incident.created_by)

    if incident.assigned_user is not None:
        recipients.append(incident.assigned_user)

    return _create_for_users(
        db,
        recipients,
        incident=incident,
        alert_type=AlertType.evidence_uploaded,
        severity=AlertSeverity.info,
        title=f"Evidence added: {incident.incident_number}",
        message=(
            f"{actor.full_name} uploaded evidence "
            f"({original_file_name}) for {incident.title}."
        ),
        action_url=f"/incidents?incident={incident.id}",
        recipient_department_id=incident.department_id,
        exclude_user_ids={actor.id},
    )



def notify_users(
    db: Session,
    *,
    recipients: Iterable[User],
    actor: User,
    incident: Incident | None,
    title: str,
    message: str,
    action_url: str | None,
    severity: AlertSeverity = AlertSeverity.info,
    alert_type: AlertType = AlertType.system,
) -> list[Alert]:
    return _create_for_users(
        db,
        recipients,
        incident=incident,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        action_url=action_url,
        recipient_department_id=incident.department_id if incident is not None else None,
        exclude_user_ids={actor.id},
    )

def mark_read(
    db: Session,
    alert: Alert,
) -> Alert:
    if not alert.is_read:
        alert.is_read = True
        alert.read_at = datetime.now(timezone.utc)
        db.add(alert)
        db.commit()
        db.refresh(alert)

    return alert


def acknowledge(
    db: Session,
    alert: Alert,
) -> Alert:
    now = datetime.now(timezone.utc)

    if not alert.is_read:
        alert.is_read = True
        alert.read_at = now

    if not alert.is_acknowledged:
        alert.is_acknowledged = True
        alert.acknowledged_at = now

    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def archive(
    db: Session,
    alert: Alert,
) -> Alert:
    if not alert.is_archived:
        alert.is_archived = True
        alert.archived_at = datetime.now(timezone.utc)

    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def mark_all_read(
    db: Session,
    user_id: int,
) -> int:
    alerts = repository.mark_all_read(
        db,
        user_id,
    )

    if not alerts:
        return 0

    now = datetime.now(timezone.utc)

    for alert in alerts:
        alert.is_read = True
        alert.read_at = now
        db.add(alert)

    db.commit()
    return len(alerts)
