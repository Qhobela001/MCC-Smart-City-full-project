from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ai_detections.models import AIDetection
from app.modules.incidents.models import (
    Incident,
    IncidentStatus,
)


TERMINAL_STATUSES = (
    IncidentStatus.resolved,
    IncidentStatus.dismissed,
)


def find_duplicate_incident(
    db: Session,
    detection: AIDetection,
    *,
    dedup_seconds: int,
) -> Incident | None:
    """
    Find an active incident that this AI detection
    most likely belongs to.

    Initial deduplication strategy:
    - same camera
    - same detection type
    - detection occurred inside the configured time window
    - incident is still active
    - ignore the current detection itself
    """

    if not detection.camera_identifier:
        return None

    window_start = (
        detection.detected_at
        - timedelta(seconds=dedup_seconds)
    )

    statement = (
        select(Incident)
        .join(
            AIDetection,
            AIDetection.incident_id == Incident.id,
        )
        .where(
            AIDetection.camera_identifier
            == detection.camera_identifier,
            AIDetection.detection_type
            == detection.detection_type,
            AIDetection.detected_at
            >= window_start,
            AIDetection.detected_at
            <= detection.detected_at,
            Incident.status.notin_(
                TERMINAL_STATUSES
            ),
        )
        .order_by(
            AIDetection.detected_at.desc(),
            AIDetection.id.desc(),
        )
        .limit(1)
    )

    if detection.id is not None:
        statement = statement.where(
            AIDetection.id != detection.id
        )

    return db.scalar(statement)