from datetime import datetime, timezone
from math import ceil
from secrets import token_hex

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import user_has_permission
from app.modules.alerts import service as alert_service
from app.modules.assignments import service as assignment_service
from app.modules.departments.models import Department
from app.modules.incidents import repository
from app.modules.incidents.models import (
    Incident,
    IncidentActivity,
    IncidentStatus,
)
from app.modules.incidents.schemas import (
    IncidentAssignment,
    IncidentCreate,
    IncidentListResponse,
    IncidentRead,
    IncidentStatusChange,
    IncidentUpdate,
)
from app.modules.users.models import User


TERMINAL_STATUSES = {
    IncidentStatus.resolved,
    IncidentStatus.dismissed,
}


ALLOWED_TRANSITIONS: dict[
    IncidentStatus,
    set[IncidentStatus],
] = {
    IncidentStatus.new: {
        IncidentStatus.under_review,
        IncidentStatus.confirmed,
        IncidentStatus.assigned,
        IncidentStatus.dismissed,
    },
    IncidentStatus.under_review: {
        IncidentStatus.confirmed,
        IncidentStatus.assigned,
        IncidentStatus.dismissed,
    },
    IncidentStatus.confirmed: {
        IncidentStatus.assigned,
        IncidentStatus.in_progress,
        IncidentStatus.dismissed,
    },
    IncidentStatus.assigned: {
        IncidentStatus.in_progress,
        IncidentStatus.resolved,
        IncidentStatus.dismissed,
    },
    IncidentStatus.in_progress: {
        IncidentStatus.resolved,
        IncidentStatus.dismissed,
    },
    IncidentStatus.resolved: set(),
    IncidentStatus.dismissed: set(),
}


def generate_incident_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = token_hex(3).upper()
    return f"MCC-INC-{date_part}-{random_part}"


def validate_department(
    db: Session,
    department_id: int | None,
) -> Department | None:
    if department_id is None:
        return None

    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    if not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected department is inactive.",
        )

    return department


def validate_assignee(
    db: Session,
    user_id: int,
    department_id: int | None,
) -> User:
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected user account is inactive.",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A SuperAdmin account cannot be assigned to an incident.",
        )

    if (
        department_id is not None
        and user.department_id != department_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The assigned user must belong to the "
                "incident department."
            ),
        )

    return user


def ensure_can_edit(
    actor: User,
    incident: Incident,
) -> None:
    if actor.is_superuser:
        return

    if user_has_permission(actor, "incidents.update"):
        return

    if incident.created_by_id == actor.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorised to update this incident.",
    )


def create_incident(
    db: Session,
    actor: User,
    payload: IncidentCreate,
) -> Incident:
    validate_department(db, payload.department_id)

    if payload.assigned_user_id is not None:
        validate_assignee(
            db,
            payload.assigned_user_id,
            payload.department_id,
        )

    incident = Incident(
        **payload.model_dump(),
        incident_number=generate_incident_number(),
        created_by_id=actor.id,
        status=(
            IncidentStatus.assigned
            if payload.assigned_user_id is not None
            else IncidentStatus.new
        ),
    )

    repository.create(db, incident)

    repository.add_activity(
        db,
        IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action="incident.created",
            previous_status=None,
            new_status=incident.status,
            notes="Incident created.",
        ),
    )

    # Flush relationship state before generating notifications.
    db.flush()
    db.refresh(incident)

    alert_service.notify_incident_created(
        db,
        incident=incident,
        actor=actor,
    )

    db.commit()
    db.refresh(incident)
    return incident


def update_incident(
    db: Session,
    actor: User,
    incident: Incident,
    payload: IncidentUpdate,
) -> Incident:
    ensure_can_edit(actor, incident)

    if incident.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolved or dismissed incidents cannot be edited.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "department_id" in update_data:
        validate_department(
            db,
            update_data["department_id"],
        )

        if (
            incident.assigned_user_id is not None
            and update_data["department_id"] is not None
        ):
            validate_assignee(
                db,
                incident.assigned_user_id,
                update_data["department_id"],
            )

    changed_fields: list[str] = []

    for field_name, value in update_data.items():
        if getattr(incident, field_name) != value:
            setattr(incident, field_name, value)
            changed_fields.append(field_name)

    if changed_fields:
        repository.add_activity(
            db,
            IncidentActivity(
                incident_id=incident.id,
                actor_user_id=actor.id,
                action="incident.updated",
                previous_status=incident.status,
                new_status=incident.status,
                notes=(
                    "Updated fields: "
                    + ", ".join(sorted(changed_fields))
                ),
            ),
        )

    repository.save(db, incident)
    db.commit()
    db.refresh(incident)
    return incident


def assign_incident(
    db: Session,
    actor: User,
    incident: Incident,
    payload: IncidentAssignment,
) -> Incident:
    assignment_service.create_from_incident_assignment(
        db,
        actor,
        incident,
        assigned_user_id=payload.assigned_user_id,
        department_id=payload.department_id,
        notes=payload.notes,
    )
    db.refresh(incident)
    return incident

def change_status(
    db: Session,
    actor: User,
    incident: Incident,
    payload: IncidentStatusChange,
) -> Incident:
    if incident.status == payload.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The incident already has that status.",
        )

    if payload.status not in ALLOWED_TRANSITIONS[incident.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Status cannot change from {incident.status.value} "
                f"to {payload.status.value}."
            ),
        )

    if payload.status == IncidentStatus.resolved:
        if not (
            actor.is_superuser
            or user_has_permission(actor, "incidents.resolve")
            or incident.assigned_user_id == actor.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorised to resolve this incident.",
            )

        if not payload.resolution_notes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resolution notes are required.",
            )

    if payload.status == IncidentStatus.dismissed:
        if not (
            actor.is_superuser
            or user_has_permission(actor, "incidents.dismiss")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission required: incidents.dismiss",
            )

    previous_status = incident.status
    incident.status = payload.status

    if payload.status in {
        IncidentStatus.under_review,
        IncidentStatus.confirmed,
        IncidentStatus.assigned,
        IncidentStatus.in_progress,
    } and incident.acknowledged_at is None:
        incident.acknowledged_at = datetime.now(timezone.utc)

    if payload.status == IncidentStatus.resolved:
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolution_notes = payload.resolution_notes
    else:
        incident.resolved_at = None

    repository.add_activity(
        db,
        IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action=f"incident.status.{payload.status.value}",
            previous_status=previous_status,
            new_status=payload.status,
            notes=payload.notes or payload.resolution_notes,
        ),
    )

    repository.save(db, incident)

    db.flush()
    db.refresh(incident)

    alert_service.notify_status_changed(
        db,
        incident=incident,
        actor=actor,
        previous_status=previous_status,
    )

    db.commit()
    db.refresh(incident)
    return incident


def to_read(incident: Incident) -> IncidentRead:
    data = IncidentRead.model_validate(incident)
    data.evidence_count = len(incident.evidence)
    return data


def to_list_response(
    incidents: list[Incident],
    total: int,
    page: int,
    page_size: int,
) -> IncidentListResponse:
    return IncidentListResponse(
        items=[to_read(incident) for incident in incidents],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
