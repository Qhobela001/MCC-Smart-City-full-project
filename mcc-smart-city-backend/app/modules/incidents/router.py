from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import (
    get_current_user,
    get_db,
    require_permission,
)
from app.modules.incidents import repository, service
from app.modules.incidents.models import (
    IncidentPriority,
    IncidentStatus,
    IncidentType,
)
from app.modules.incidents.schemas import (
    IncidentActivityRead,
    IncidentAssignment,
    IncidentCreate,
    IncidentListResponse,
    IncidentRead,
    IncidentStatusChange,
    IncidentUpdate,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.get(
    "",
    response_model=IncidentListResponse,
)
def list_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    incident_status: IncidentStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority: IncidentPriority | None = None,
    incident_type: IncidentType | None = None,
    department_id: int | None = None,
    assigned_user_id: int | None = None,
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("incidents.view")
    ),
) -> IncidentListResponse:
    incidents, total = repository.list_incidents(
        db,
        actor,
        page=page,
        page_size=page_size,
        status_value=incident_status,
        priority=priority,
        incident_type=incident_type,
        department_id=department_id,
        assigned_user_id=assigned_user_id,
        search=search,
    )

    return service.to_list_response(
        incidents,
        total,
        page,
        page_size,
    )


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("incidents.create")
    ),
) -> IncidentRead:
    incident = service.create_incident(
        db,
        actor,
        payload,
    )
    return service.to_read(incident)


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("incidents.view")
    ),
) -> IncidentRead:
    incident = repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    return service.to_read(incident)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> IncidentRead:
    incident = repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    updated = service.update_incident(
        db,
        actor,
        incident,
        payload,
    )
    return service.to_read(updated)


@router.post(
    "/{incident_id}/assign",
    response_model=IncidentRead,
)
def assign_incident(
    incident_id: int,
    payload: IncidentAssignment,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("incidents.assign")
    ),
) -> IncidentRead:
    incident = repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    assigned = service.assign_incident(
        db,
        actor,
        incident,
        payload,
    )
    return service.to_read(assigned)


@router.post(
    "/{incident_id}/status",
    response_model=IncidentRead,
)
def change_incident_status(
    incident_id: int,
    payload: IncidentStatusChange,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> IncidentRead:
    incident = repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    updated = service.change_status(
        db,
        actor,
        incident,
        payload,
    )
    return service.to_read(updated)


@router.get(
    "/{incident_id}/timeline",
    response_model=list[IncidentActivityRead],
)
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("incidents.view")
    ),
) -> list[IncidentActivityRead]:
    incident = repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    return repository.list_activities(
        db,
        incident.id,
    )
