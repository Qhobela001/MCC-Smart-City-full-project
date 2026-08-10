from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.alerts import repository, service
from app.modules.alerts.schemas import (
    AlertActionResponse,
    AlertListResponse,
    AlertRead,
    UnreadCountResponse,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts & Notifications"],
)


@router.get(
    "",
    response_model=AlertListResponse,
)
def list_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = False,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertListResponse:
    items, total = repository.list_for_user(
        db,
        current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
        include_archived=include_archived,
    )

    return AlertListResponse(
        items=items,
        total=total,
        unread_count=repository.unread_count(
            db,
            current_user.id,
        ),
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    return UnreadCountResponse(
        unread_count=repository.unread_count(
            db,
            current_user.id,
        )
    )


@router.get(
    "/{alert_id}",
    response_model=AlertRead,
)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRead:
    alert = repository.get_for_user(
        db,
        alert_id,
        current_user.id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return alert


@router.patch(
    "/{alert_id}/read",
    response_model=AlertRead,
)
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRead:
    alert = repository.get_for_user(
        db,
        alert_id,
        current_user.id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return service.mark_read(db, alert)


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=AlertRead,
)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRead:
    alert = repository.get_for_user(
        db,
        alert_id,
        current_user.id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return service.acknowledge(db, alert)


@router.patch(
    "/{alert_id}/archive",
    response_model=AlertRead,
)
def archive_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRead:
    alert = repository.get_for_user(
        db,
        alert_id,
        current_user.id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return service.archive(db, alert)


@router.patch(
    "/read-all",
    response_model=AlertActionResponse,
)
def mark_all_alerts_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertActionResponse:
    service.mark_all_read(
        db,
        current_user.id,
    )
    return AlertActionResponse(success=True)
