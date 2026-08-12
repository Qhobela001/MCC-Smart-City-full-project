from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.deps import (
    get_db,
    require_permission,
)
from app.modules.ai_detections import (
    repository,
    service,
)
from app.modules.ai_detections.models import (
    DetectionReviewStatus,
    DetectionSource,
    DetectionType,
)
from app.modules.ai_detections.schemas import (
    AIDetectionBatchCreate,
    AIDetectionBatchResponse,
    AIDetectionCreate,
    AIDetectionListResponse,
    AIDetectionRead,
    AIDetectionReview,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/ai-detections",
    tags=["AI Detections"],
)


@router.get(
    "",
    response_model=AIDetectionListResponse,
)
def list_detections(
        page: int = Query(
            default=1,
            ge=1,
        ),
        page_size: int = Query(
            default=20,
            ge=1,
            le=100,
        ),
        detection_type: DetectionType | None = None,
        source_type: DetectionSource | None = None,
        review_status: DetectionReviewStatus | None = None,
        camera_identifier: str | None = Query(
            default=None,
            max_length=100,
        ),
        model_name: str | None = Query(
            default=None,
            max_length=150,
        ),
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_confidence: float | None = Query(
            default=None,
            ge=0.0,
            le=1.0,
        ),
        incident_id: int | None = None,
        is_test: bool | None = None,
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "ai_detections.view"
            )
        ),
) -> AIDetectionListResponse:
    items, total = (
        repository.list_detections(
            db,
            page=page,
            page_size=page_size,
            detection_type=detection_type,
            source_type=source_type,
            review_status=review_status,
            camera_identifier=(
                camera_identifier
            ),
            model_name=model_name,
            date_from=date_from,
            date_to=date_to,
            min_confidence=min_confidence,
            incident_id=incident_id,
            is_test=is_test,
        )
    )

    return service.to_list_response(
        items,
        total,
        page,
        page_size,
    )


@router.post(
    "/batch",
    response_model=AIDetectionBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detection_batch(
        payload: AIDetectionBatchCreate,
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "ai_detections.create"
            )
        ),
) -> AIDetectionBatchResponse:
    return service.create_detection_batch(
        db,
        payload,
        actor=actor,
    )


@router.post(
    "",
    response_model=AIDetectionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_detection(
        payload: AIDetectionCreate,
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "ai_detections.create"
            )
        ),
) -> AIDetectionRead:
    detection = service.create_detection(
        db,
        payload,
        actor=actor,
    )

    return service.to_read(
        detection
    )


@router.get(
    "/{detection_id}",
    response_model=AIDetectionRead,
)
def get_detection(
        detection_id: int,
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "ai_detections.view"
            )
        ),
) -> AIDetectionRead:
    detection = (
        service.get_detection_or_404(
            db,
            detection_id,
        )
    )

    return service.to_read(
        detection
    )


@router.patch(
    "/{detection_id}/review",
    response_model=AIDetectionRead,
)
def review_detection(
        detection_id: int,
        payload: AIDetectionReview,
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "ai_detections.review"
            )
        ),
) -> AIDetectionRead:
    detection = (
        service.get_detection_or_404(
            db,
            detection_id,
        )
    )

    detection = (
        service.review_detection(
            db,
            detection,
            review_status=(
                payload.review_status
            ),
            actor=actor,
        )
    )

    return service.to_read(
        detection
    )