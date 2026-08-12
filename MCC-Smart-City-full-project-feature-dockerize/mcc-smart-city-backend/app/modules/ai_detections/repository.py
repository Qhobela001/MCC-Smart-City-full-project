import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.ai_detections.models import (
    AIDetection,
    DetectionReviewStatus,
    DetectionSource,
    DetectionType,
)
from app.modules.ai_detections.schemas import AIDetectionCreate


def create_detection(
        db: Session,
        payload: AIDetectionCreate,
        *,
        commit: bool = True,
) -> AIDetection:
    data = payload.model_dump()

    if not data.get("detection_uuid"):
        data["detection_uuid"] = str(uuid.uuid4())

    detection = AIDetection(**data)

    db.add(detection)

    # Required so detection.id exists before the
    # incident engine processes the detection.
    db.flush()

    if commit:
        db.commit()
        db.refresh(detection)

    return detection


def create_detection_batch(
        db: Session,
        payloads: list[AIDetectionCreate],
        *,
        commit: bool = True,
) -> list[AIDetection]:
    detections: list[AIDetection] = []

    try:
        for payload in payloads:
            data = payload.model_dump()

            if not data.get("detection_uuid"):
                data["detection_uuid"] = str(uuid.uuid4())

            detection = AIDetection(**data)

            db.add(detection)
            detections.append(detection)

        # Allocate IDs before the incident engine runs.
        db.flush()

        if commit:
            db.commit()

            for detection in detections:
                db.refresh(detection)

        return detections

    except Exception:
        db.rollback()
        raise


def get_detection(
        db: Session,
        detection_id: int,
) -> AIDetection | None:
    return (
        db.query(AIDetection)
        .filter(AIDetection.id == detection_id)
        .first()
    )


def get_detection_by_uuid(
        db: Session,
        detection_uuid: str,
) -> AIDetection | None:
    return (
        db.query(AIDetection)
        .filter(
            AIDetection.detection_uuid == detection_uuid
        )
        .first()
    )


def list_detections(
        db: Session,
        *,
        page: int,
        page_size: int,
        detection_type: DetectionType | None = None,
        source_type: DetectionSource | None = None,
        review_status: DetectionReviewStatus | None = None,
        camera_identifier: str | None = None,
        model_name: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_confidence: float | None = None,
        incident_id: int | None = None,
        is_test: bool | None = None,
) -> tuple[list[AIDetection], int]:
    query = db.query(AIDetection)

    if detection_type is not None:
        query = query.filter(
            AIDetection.detection_type == detection_type
        )

    if source_type is not None:
        query = query.filter(
            AIDetection.source_type == source_type
        )

    if review_status is not None:
        query = query.filter(
            AIDetection.review_status == review_status
        )

    if camera_identifier:
        query = query.filter(
            AIDetection.camera_identifier == camera_identifier
        )

    if model_name:
        query = query.filter(
            AIDetection.model_name == model_name
        )

    if date_from is not None:
        query = query.filter(
            AIDetection.detected_at >= date_from
        )

    if date_to is not None:
        query = query.filter(
            AIDetection.detected_at <= date_to
        )

    if min_confidence is not None:
        query = query.filter(
            AIDetection.confidence >= min_confidence
        )

    if incident_id is not None:
        query = query.filter(
            AIDetection.incident_id == incident_id
        )

    if is_test is not None:
        query = query.filter(
            AIDetection.is_test == is_test
        )

    total = query.count()

    items = (
        query
        .order_by(
            AIDetection.detected_at.desc(),
            AIDetection.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return items, total


def review_detection(
        db: Session,
        detection: AIDetection,
        *,
        review_status: DetectionReviewStatus,
        reviewed_by_id: int,
        reviewed_at: datetime,
) -> AIDetection:
    detection.review_status = review_status
    detection.reviewed_by_id = reviewed_by_id
    detection.reviewed_at = reviewed_at

    db.commit()
    db.refresh(detection)

    return detection