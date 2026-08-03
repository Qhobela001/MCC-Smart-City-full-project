from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.incidents.models import (
    Incident,
    IncidentActivity,
    IncidentPriority,
    IncidentStatus,
    IncidentType,
)
from app.modules.users.models import User


def visible_incident_filter(actor: User):
    if actor.is_superuser:
        return True

    conditions = [
        Incident.created_by_id == actor.id,
        Incident.assigned_user_id == actor.id,
    ]

    if actor.department_id is not None:
        conditions.append(
            Incident.department_id == actor.department_id
        )

    return or_(*conditions)


def list_incidents(
    db: Session,
    actor: User,
    *,
    page: int,
    page_size: int,
    status_value: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    incident_type: IncidentType | None = None,
    department_id: int | None = None,
    assigned_user_id: int | None = None,
    search: str | None = None,
) -> tuple[list[Incident], int]:
    filters = [visible_incident_filter(actor)]

    if status_value is not None:
        filters.append(Incident.status == status_value)

    if priority is not None:
        filters.append(Incident.priority == priority)

    if incident_type is not None:
        filters.append(Incident.incident_type == incident_type)

    if department_id is not None:
        filters.append(Incident.department_id == department_id)

    if assigned_user_id is not None:
        filters.append(
            Incident.assigned_user_id == assigned_user_id
        )

    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Incident.incident_number.ilike(pattern),
                Incident.title.ilike(pattern),
                Incident.description.ilike(pattern),
                Incident.location_name.ilike(pattern),
            )
        )

    count_statement = (
        select(func.count(Incident.id))
        .where(*filters)
    )
    total = int(db.scalar(count_statement) or 0)

    statement = (
        select(Incident)
        .where(*filters)
        .order_by(
            Incident.created_at.desc(),
            Incident.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    incidents = list(
        db.scalars(statement).unique().all()
    )
    return incidents, total


def get_visible(
    db: Session,
    actor: User,
    incident_id: int,
) -> Incident | None:
    statement = (
        select(Incident)
        .where(
            Incident.id == incident_id,
            visible_incident_filter(actor),
        )
    )
    return db.scalar(statement)


def get_by_number(
    db: Session,
    incident_number: str,
) -> Incident | None:
    return db.scalar(
        select(Incident).where(
            Incident.incident_number == incident_number
        )
    )


def create(
    db: Session,
    incident: Incident,
) -> Incident:
    db.add(incident)
    db.flush()
    return incident


def save(
    db: Session,
    incident: Incident,
) -> Incident:
    db.add(incident)
    db.flush()
    return incident


def add_activity(
    db: Session,
    activity: IncidentActivity,
) -> IncidentActivity:
    db.add(activity)
    db.flush()
    return activity


def list_activities(
    db: Session,
    incident_id: int,
) -> list[IncidentActivity]:
    statement = (
        select(IncidentActivity)
        .where(
            IncidentActivity.incident_id == incident_id
        )
        .order_by(
            IncidentActivity.created_at.asc(),
            IncidentActivity.id.asc(),
        )
    )
    return list(
        db.scalars(statement).unique().all()
    )
