from datetime import datetime

from sqlalchemy import (
    Integer,
    case,
    cast,
    func,
)
from sqlalchemy.orm import Query, Session

from app.modules.ai_detections.models import (
    AIDetection,
    DetectionReviewStatus,
    DetectionType,
)


def apply_filters(
        query: Query,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        detection_type: DetectionType | None = None,
        camera_identifier: str | None = None,
        model_name: str | None = None,
        min_confidence: float | None = None,
        include_test: bool = False,
) -> Query:
    if date_from is not None:
        query = query.filter(
            AIDetection.detected_at >= date_from
        )

    if date_to is not None:
        query = query.filter(
            AIDetection.detected_at <= date_to
        )

    if detection_type is not None:
        query = query.filter(
            AIDetection.detection_type == detection_type
        )

    if camera_identifier:
        query = query.filter(
            AIDetection.camera_identifier == camera_identifier
        )

    if model_name:
        query = query.filter(
            AIDetection.model_name == model_name
        )

    if min_confidence is not None:
        query = query.filter(
            AIDetection.confidence >= min_confidence
        )

    if not include_test:
        query = query.filter(
            AIDetection.is_test.is_(False)
        )

    return query


def get_overview(
        db: Session,
        **filters,
):
    query = db.query(
        func.count(AIDetection.id).label(
            "total_detections"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
        func.count(
            func.distinct(AIDetection.camera_identifier)
        ).label("unique_cameras"),
        func.count(
            func.distinct(AIDetection.location_name)
        ).label("unique_locations"),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.unreviewed,
                    1,
                ),
                else_=0,
            )
        ).label("unreviewed"),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.confirmed,
                    1,
                ),
                else_=0,
            )
        ).label("confirmed"),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.rejected,
                    1,
                ),
                else_=0,
            )
        ).label("rejected"),
        func.min(AIDetection.detected_at).label(
            "earliest_detection"
        ),
        func.max(AIDetection.detected_at).label(
            "latest_detection"
        ),
    )

    query = apply_filters(
        query,
        **filters,
    )

    return query.one()


def get_by_type(
        db: Session,
        **filters,
):
    query = db.query(
        AIDetection.detection_type.label(
            "detection_type"
        ),
        func.count(AIDetection.id).label(
            "count"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(AIDetection.detection_type)
        .order_by(
            func.count(AIDetection.id).desc()
        )
        .all()
    )


def get_trend(
        db: Session,
        **filters,
):
    detection_date = func.date(
        AIDetection.detected_at
    )

    query = db.query(
        detection_date.label("date"),
        func.count(AIDetection.id).label(
            "count"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(detection_date)
        .order_by(detection_date.asc())
        .all()
    )


def get_by_location(
        db: Session,
        **filters,
):
    query = db.query(
        AIDetection.location_name.label(
            "location_name"
        ),
        func.count(AIDetection.id).label(
            "count"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
    ).filter(
        AIDetection.location_name.isnot(None)
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(AIDetection.location_name)
        .order_by(
            func.count(AIDetection.id).desc()
        )
        .all()
    )


def get_by_camera(
        db: Session,
        **filters,
):
    query = db.query(
        AIDetection.camera_identifier.label(
            "camera_identifier"
        ),
        func.count(AIDetection.id).label(
            "count"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
        func.max(AIDetection.detected_at).label(
            "latest_detection"
        ),
    ).filter(
        AIDetection.camera_identifier.isnot(None)
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(AIDetection.camera_identifier)
        .order_by(
            func.count(AIDetection.id).desc()
        )
        .all()
    )


def get_by_hour(
        db: Session,
        **filters,
):
    detection_hour = cast(
        func.extract(
            "hour",
            AIDetection.detected_at,
        ),
        Integer,
    )

    query = db.query(
        detection_hour.label("hour"),
        func.count(AIDetection.id).label(
            "count"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(detection_hour)
        .order_by(detection_hour.asc())
        .all()
    )


def get_model_performance(
        db: Session,
        **filters,
):
    query = db.query(
        AIDetection.model_name.label(
            "model_name"
        ),
        AIDetection.model_version.label(
            "model_version"
        ),
        func.count(AIDetection.id).label(
            "detections"
        ),
        func.avg(AIDetection.confidence).label(
            "average_confidence"
        ),
        func.min(AIDetection.confidence).label(
            "minimum_confidence"
        ),
        func.max(AIDetection.confidence).label(
            "maximum_confidence"
        ),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.unreviewed,
                    1,
                ),
                else_=0,
            )
        ).label("unreviewed"),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.confirmed,
                    1,
                ),
                else_=0,
            )
        ).label("confirmed"),
        func.sum(
            case(
                (
                    AIDetection.review_status
                    == DetectionReviewStatus.rejected,
                    1,
                ),
                else_=0,
            )
        ).label("rejected"),
    )

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .group_by(
            AIDetection.model_name,
            AIDetection.model_version,
        )
        .order_by(
            func.count(AIDetection.id).desc()
        )
        .all()
    )


def get_recent(
        db: Session,
        *,
        limit: int,
        **filters,
):
    query = db.query(AIDetection)

    query = apply_filters(
        query,
        **filters,
    )

    return (
        query
        .order_by(
            AIDetection.detected_at.desc(),
            AIDetection.id.desc(),
        )
        .limit(limit)
        .all()
    )