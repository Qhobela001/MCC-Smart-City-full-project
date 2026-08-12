from sqlalchemy.orm import Session

from app.modules.ai_detections.schemas import (
    AIDetectionRead,
)
from app.modules.analytics import repository
from app.modules.analytics.schemas import (
    AnalyticsOverview,
    CameraAnalytics,
    DetectionTypeAnalytics,
    HourAnalytics,
    LocationAnalytics,
    ModelPerformanceAnalytics,
    RecentDetectionsResponse,
    TrendPoint,
)


def _confidence(value) -> float:
    if value is None:
        return 0.0

    return round(float(value), 4)


def get_overview(
        db: Session,
        **filters,
) -> AnalyticsOverview:
    row = repository.get_overview(
        db,
        **filters,
    )

    return AnalyticsOverview(
        total_detections=int(
            row.total_detections or 0
        ),
        average_confidence=_confidence(
            row.average_confidence
        ),
        unique_cameras=int(
            row.unique_cameras or 0
        ),
        unique_locations=int(
            row.unique_locations or 0
        ),
        unreviewed=int(
            row.unreviewed or 0
        ),
        confirmed=int(
            row.confirmed or 0
        ),
        rejected=int(
            row.rejected or 0
        ),
        earliest_detection=row.earliest_detection,
        latest_detection=row.latest_detection,
    )


def get_by_type(
        db: Session,
        **filters,
) -> list[DetectionTypeAnalytics]:
    rows = repository.get_by_type(
        db,
        **filters,
    )

    total = sum(
        int(row.count or 0)
        for row in rows
    )

    result: list[DetectionTypeAnalytics] = []

    for row in rows:
        count = int(row.count or 0)

        percentage = (
            (count / total) * 100
            if total > 0
            else 0.0
        )

        result.append(
            DetectionTypeAnalytics(
                detection_type=row.detection_type,
                count=count,
                average_confidence=_confidence(
                    row.average_confidence
                ),
                percentage=round(
                    percentage,
                    2,
                ),
            )
        )

    return result


def get_trend(
        db: Session,
        **filters,
) -> list[TrendPoint]:
    rows = repository.get_trend(
        db,
        **filters,
    )

    return [
        TrendPoint(
            date=row.date,
            count=int(row.count or 0),
            average_confidence=_confidence(
                row.average_confidence
            ),
        )
        for row in rows
    ]


def get_by_location(
        db: Session,
        **filters,
) -> list[LocationAnalytics]:
    rows = repository.get_by_location(
        db,
        **filters,
    )

    return [
        LocationAnalytics(
            location_name=row.location_name,
            count=int(row.count or 0),
            average_confidence=_confidence(
                row.average_confidence
            ),
        )
        for row in rows
    ]


def get_by_camera(
        db: Session,
        **filters,
) -> list[CameraAnalytics]:
    rows = repository.get_by_camera(
        db,
        **filters,
    )

    return [
        CameraAnalytics(
            camera_identifier=(
                row.camera_identifier
            ),
            count=int(row.count or 0),
            average_confidence=_confidence(
                row.average_confidence
            ),
            latest_detection=(
                row.latest_detection
            ),
        )
        for row in rows
    ]


def get_by_hour(
        db: Session,
        **filters,
) -> list[HourAnalytics]:
    rows = repository.get_by_hour(
        db,
        **filters,
    )

    return [
        HourAnalytics(
            hour=int(row.hour),
            count=int(row.count or 0),
            average_confidence=_confidence(
                row.average_confidence
            ),
        )
        for row in rows
    ]


def get_model_performance(
        db: Session,
        **filters,
) -> list[ModelPerformanceAnalytics]:
    rows = repository.get_model_performance(
        db,
        **filters,
    )

    return [
        ModelPerformanceAnalytics(
            model_name=row.model_name,
            model_version=row.model_version,
            detections=int(
                row.detections or 0
            ),
            average_confidence=_confidence(
                row.average_confidence
            ),
            minimum_confidence=_confidence(
                row.minimum_confidence
            ),
            maximum_confidence=_confidence(
                row.maximum_confidence
            ),
            unreviewed=int(
                row.unreviewed or 0
            ),
            confirmed=int(
                row.confirmed or 0
            ),
            rejected=int(
                row.rejected or 0
            ),
        )
        for row in rows
    ]


def get_recent(
        db: Session,
        *,
        limit: int,
        **filters,
) -> RecentDetectionsResponse:
    detections = repository.get_recent(
        db,
        limit=limit,
        **filters,
    )

    return RecentDetectionsResponse(
        items=[
            AIDetectionRead.model_validate(
                detection
            )
            for detection in detections
        ]
    )