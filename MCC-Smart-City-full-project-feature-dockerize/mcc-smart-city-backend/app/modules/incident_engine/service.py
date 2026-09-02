from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.ai_detections.models import AIDetection
from app.modules.alerts import repository as alert_repository
from app.modules.alerts.models import (
    Alert,
    AlertSeverity,
    AlertType,
)
from app.modules.incident_engine import repository, rules
from app.modules.incidents import repository as incident_repository
from app.modules.incidents.models import (
    Incident,
    IncidentActivity,
    IncidentPriority,
    IncidentSource,
    IncidentStatus,
    IncidentType,
)
from app.modules.incidents.service import generate_incident_number
from app.modules.users.models import User
from app.core.deps import user_has_permission


@dataclass
class IncidentEngineResult:
    decision: str
    incident: Incident | None = None
    alerts_created: int = 0


def _severity_from_priority(
    priority: IncidentPriority,
) -> AlertSeverity:
    mapping = {
        IncidentPriority.low: AlertSeverity.low,
        IncidentPriority.medium: AlertSeverity.medium,
        IncidentPriority.high: AlertSeverity.high,
        IncidentPriority.critical: AlertSeverity.critical,
    }

    return mapping[priority]


def _set_engine_metadata(
    detection: AIDetection,
    *,
    decision: str,
    incident_id: int | None = None,
    threshold: float | None = None,
    dedup_seconds: int | None = None,
    notes: str | None = None,
) -> None:
    attributes = dict(detection.attributes or {})

    metadata: dict[str, object] = {
        "decision": decision,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    if incident_id is not None:
        metadata["incident_id"] = incident_id

    if threshold is not None:
        metadata["confidence_threshold"] = threshold

    if dedup_seconds is not None:
        metadata["dedup_seconds"] = dedup_seconds

    if notes:
        metadata["notes"] = notes

    attributes["incident_engine"] = metadata
    detection.attributes = attributes


def _create_ai_alerts(
    db: Session,
    *,
    incident: Incident,
    detection: AIDetection,
) -> list[Alert]:
    recipients = alert_repository.active_superadmins(db)

    created: list[Alert] = []

    severity = _severity_from_priority(
        incident.priority
    )

    camera_name = (
        detection.camera_identifier
        or "Unknown camera"
    )

    for recipient in recipients:
        alert = Alert(
            recipient_user_id=recipient.id,
            recipient_department_id=incident.department_id,
            incident_id=incident.id,
            alert_type=AlertType.incident_created,
            severity=severity,
            title=f"AI incident detected: {incident.title}",
            message=(
                f"{incident.incident_number} was automatically "
                f"generated from {camera_name}. "
                f"AI confidence: "
                f"{detection.confidence * 100:.1f}%."
            ),
            action_url=f"/incidents?incident={incident.id}",
        )

        alert_repository.create(
            db,
            alert,
        )

        created.append(alert)

    return created


def process_detection(
    db: Session,
    detection: AIDetection,
    *,
    actor: User,
) -> IncidentEngineResult:
    """
    Process one persisted AI detection.

    No commit is performed here. The AI detection service
    owns the transaction so detection, incident and alerts
    succeed or fail together.
    """

    if detection.incident_id is not None:
        _set_engine_metadata(
            detection,
            decision="already_linked",
            incident_id=detection.incident_id,
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="already_linked",
            incident=db.get(
                Incident,
                detection.incident_id,
            ),
        )

    # Never turn development/test detections into
    # operational incidents.
    if detection.is_test:
        _set_engine_metadata(
            detection,
            decision="skipped_test",
            notes=(
                "Test detections are stored for analytics "
                "but do not create incidents."
            ),
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="skipped_test",
        )

    # A qualified production event with completed evidence must be reviewed
    # by an authorised MCC operator. It must never bypass the review queue.
    attributes = detection.attributes or {}
    if (
        rules.is_production_camera_detection(detection)
        and detection.camera_identifier
        and attributes.get("qualification")
        and attributes.get("evidence")
    ):
        _set_engine_metadata(
            detection,
            decision="awaiting_human_review",
            notes="Qualified production event is waiting for operator review.",
        )
        db.add(detection)
        recipients = [
            user for user in alert_repository.active_superadmins(db)
            if user_has_permission(user, "ai_detections.review")
        ]
        for recipient in recipients:
            alert_repository.create(db, Alert(
                recipient_user_id=recipient.id,
                recipient_department_id=recipient.department_id,
                incident_id=None,
                alert_type=AlertType.system,
                severity=AlertSeverity.high,
                title=f"AI event awaiting review: {detection.detection_type.value.replace('_', ' ').title()}",
                message=(f"{detection.camera_identifier or 'Unknown camera'} produced a qualified "
                         f"event at {detection.location_name or 'an unassigned location'}."),
                action_url=f"/ai-review?detection={detection.id}",
            ))
        db.flush()
        return IncidentEngineResult(
            decision="awaiting_human_review",
            alerts_created=len(recipients),
        )

    # Automatic incident generation currently accepts
    # production camera detections only.
    if not rules.is_production_camera_detection(
        detection
    ):
        _set_engine_metadata(
            detection,
            decision="unsupported_source",
            notes=(
                "Automatic incident creation currently "
                "accepts live camera detections only."
            ),
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="unsupported_source",
        )

    if not detection.camera_identifier:
        _set_engine_metadata(
            detection,
            decision="missing_camera",
            notes=(
                "Camera identifier is required for "
                "automatic incident creation."
            ),
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="missing_camera",
        )

    rule = rules.get_rule(detection)

    if not rule.auto_create:
        _set_engine_metadata(
            detection,
            decision="manual_review_required",
            threshold=rule.min_confidence,
            dedup_seconds=rule.dedup_seconds,
            notes=(
                "This detection category is not "
                "configured for automatic incident "
                "creation."
            ),
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="manual_review_required",
        )

    if detection.confidence < rule.min_confidence:
        _set_engine_metadata(
            detection,
            decision="below_confidence_threshold",
            threshold=rule.min_confidence,
            dedup_seconds=rule.dedup_seconds,
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="below_confidence_threshold",
        )

    existing_incident = (
        repository.find_duplicate_incident(
            db,
            detection,
            dedup_seconds=rule.dedup_seconds,
        )
    )

    if existing_incident is not None:
        detection.incident_id = existing_incident.id

        _set_engine_metadata(
            detection,
            decision="deduplicated",
            incident_id=existing_incident.id,
            threshold=rule.min_confidence,
            dedup_seconds=rule.dedup_seconds,
            notes=(
                "Detection linked to an existing "
                "active incident."
            ),
        )

        db.add(detection)
        db.flush()

        return IncidentEngineResult(
            decision="deduplicated",
            incident=existing_incident,
        )

    priority = rules.priority_for_detection(
        detection,
        rule,
    )

    incident = Incident(
        incident_number=generate_incident_number(),
        incident_type=IncidentType(
            detection.detection_type.value
        ),
        title=rules.incident_title(
            detection
        ),
        description=rules.incident_description(
            detection
        ),
        priority=priority,
        status=IncidentStatus.new,
        source=IncidentSource.ai_detection,
        department_id=None,
        assigned_user_id=None,
        created_by_id=actor.id,
        location_name=detection.location_name,
        latitude=detection.latitude,
        longitude=detection.longitude,
        is_ai_generated=True,
        reported_at=detection.detected_at,
    )

    incident_repository.create(
        db,
        incident,
    )

    detection.incident_id = incident.id

    _set_engine_metadata(
        detection,
        decision="incident_created",
        incident_id=incident.id,
        threshold=rule.min_confidence,
        dedup_seconds=rule.dedup_seconds,
    )

    db.add(detection)

    incident_repository.add_activity(
        db,
        IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action="incident.ai_created",
            previous_status=None,
            new_status=IncidentStatus.new,
            notes=(
                f"Automatically generated from AI detection "
                f"{detection.detection_uuid} "
                f"from camera "
                f"{detection.camera_identifier}."
            ),
        ),
    )

    db.flush()

    alerts = _create_ai_alerts(
        db,
        incident=incident,
        detection=detection,
    )

    db.flush()

    return IncidentEngineResult(
        decision="incident_created",
        incident=incident,
        alerts_created=len(alerts),
    )
