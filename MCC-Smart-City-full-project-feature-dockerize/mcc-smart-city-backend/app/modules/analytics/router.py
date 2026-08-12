from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.core.deps import (
    get_db,
    require_permission,
)
from app.modules.ai_detections.models import (
    DetectionType,
)
from app.modules.analytics import service
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
from app.modules.users.models import User


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


def analytics_filters(
        date_from: datetime | None = Query(
            default=None,
        ),
        date_to: datetime | None = Query(
            default=None,
        ),
        detection_type: DetectionType | None = Query(
            default=None,
        ),
        camera_identifier: str | None = Query(
            default=None,
            max_length=100,
        ),
        model_name: str | None = Query(
            default=None,
            max_length=150,
        ),
        min_confidence: float | None = Query(
            default=None,
            ge=0.0,
            le=1.0,
        ),
        include_test: bool = Query(
            default=False,
            description=(
                    "Include detections marked as test data."
            ),
        ),
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "detection_type": detection_type,
        "camera_identifier": camera_identifier,
        "model_name": model_name,
        "min_confidence": min_confidence,
        "include_test": include_test,
    }


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
)
def overview(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> AnalyticsOverview:
    return service.get_overview(
        db,
        **filters,
    )


@router.get(
    "/by-type",
    response_model=list[DetectionTypeAnalytics],
)
def by_type(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[DetectionTypeAnalytics]:
    return service.get_by_type(
        db,
        **filters,
    )


@router.get(
    "/trend",
    response_model=list[TrendPoint],
)
def trend(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[TrendPoint]:
    return service.get_trend(
        db,
        **filters,
    )


@router.get(
    "/by-location",
    response_model=list[LocationAnalytics],
)
def by_location(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[LocationAnalytics]:
    return service.get_by_location(
        db,
        **filters,
    )


@router.get(
    "/by-camera",
    response_model=list[CameraAnalytics],
)
def by_camera(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[CameraAnalytics]:
    return service.get_by_camera(
        db,
        **filters,
    )


@router.get(
    "/by-hour",
    response_model=list[HourAnalytics],
)
def by_hour(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[HourAnalytics]:
    return service.get_by_hour(
        db,
        **filters,
    )


@router.get(
    "/model-performance",
    response_model=list[
        ModelPerformanceAnalytics
    ],
)
def model_performance(
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> list[ModelPerformanceAnalytics]:
    return service.get_model_performance(
        db,
        **filters,
    )


@router.get(
    "/recent",
    response_model=RecentDetectionsResponse,
)
def recent(
        limit: int = Query(
            default=10,
            ge=1,
            le=100,
        ),
        filters: dict = Depends(
            analytics_filters
        ),
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission("reports.view")
        ),
) -> RecentDetectionsResponse:
    return service.get_recent(
        db,
        limit=limit,
        **filters,
    )