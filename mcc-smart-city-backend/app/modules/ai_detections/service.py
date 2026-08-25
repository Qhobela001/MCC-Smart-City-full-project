import math
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.ai_detections import repository
from app.modules.ai_detections.models import (
    AIDetection,
    DetectionReviewStatus,
)
from app.modules.ai_detections.schemas import (
    AIDetectionBatchCreate,
    AIDetectionBatchResponse,
    AIDetectionCreate,
    AIDetectionListResponse,
    AIDetectionRead,
)
from app.modules.incident_engine import (
    service as incident_engine_service,
)
from app.modules.users.models import User


def create_detection(
    db: Session,
    payload: AIDetectionCreate,
    *,
    actor: User,
) -> AIDetection:
    if payload.detection_uuid:
        existing = repository.get_detection_by_uuid(
            db,
            payload.detection_uuid,
        )

        if existing:
            return existing

    try:
        # Do not commit here yet.
        # Detection + incident + alert must succeed
        # or fail together.
        detection = repository.create_detection(
            db,
            payload,
            commit=False,
        )

        incident_engine_service.process_detection(
            db,
            detection,
            actor=actor,
        )

        db.commit()
        db.refresh(detection)

        return detection

    except IntegrityError:
        db.rollback()

        if payload.detection_uuid:
            existing = repository.get_detection_by_uuid(
                db,
                payload.detection_uuid,
            )

            if existing:
                return existing

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Detection could not be persisted "
                "because of a database conflict."
            ),
        )

    except Exception:
        db.rollback()
        raise


def create_detection_batch(
    db: Session,
    payload: AIDetectionBatchCreate,
    *,
    actor: User,
) -> AIDetectionBatchResponse:
    unique_payloads: list[AIDetectionCreate] = []
    existing_items: list[AIDetection] = []

    seen_uuids: set[str] = set()

    for item in payload.detections:
        if item.detection_uuid:
            if item.detection_uuid in seen_uuids:
                continue

            seen_uuids.add(item.detection_uuid)

            existing = repository.get_detection_by_uuid(
                db,
                item.detection_uuid,
            )

            if existing:
                existing_items.append(existing)
                continue

        unique_payloads.append(item)

    try:
        created_items = repository.create_detection_batch(
            db,
            unique_payloads,
            commit=False,
        )

        for detection in created_items:
            incident_engine_service.process_detection(
                db,
                detection,
                actor=actor,
            )

        db.commit()

        for detection in created_items:
            db.refresh(detection)

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "One or more detections could not be "
                "persisted because of a database conflict."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise

    items = existing_items + created_items

    return AIDetectionBatchResponse(
        created=len(created_items),
        items=[
            AIDetectionRead.model_validate(item)
            for item in items
        ],
    )


def get_detection_or_404(
    db: Session,
    detection_id: int,
) -> AIDetection:
    detection = repository.get_detection(
        db,
        detection_id,
    )

    if detection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI detection not found.",
        )

    return detection


def review_detection(
    db: Session,
    detection: AIDetection,
    *,
    review_status: DetectionReviewStatus,
    actor: User,
) -> AIDetection:
    return repository.review_detection(
        db,
        detection,
        review_status=review_status,
        reviewed_by_id=actor.id,
        reviewed_at=datetime.now(timezone.utc),
    )


def to_read(
    detection: AIDetection,
) -> AIDetectionRead:
    return AIDetectionRead.model_validate(detection)


def to_list_response(
    items: list[AIDetection],
    total: int,
    page: int,
    page_size: int,
) -> AIDetectionListResponse:
    pages = (
        math.ceil(total / page_size)
        if total > 0
        else 0
    )

    return AIDetectionListResponse(
        items=[
            AIDetectionRead.model_validate(item)
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )