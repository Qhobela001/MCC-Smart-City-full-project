from app.modules.ai_detections.models import (
    AIDetection,
    DetectionSource,
)
from app.modules.incident_engine.config import (
    INCIDENT_RULES,
    IncidentRule,
)
from app.modules.incidents.models import IncidentPriority


_PRIORITY_RANK = {
    IncidentPriority.low: 1,
    IncidentPriority.medium: 2,
    IncidentPriority.high: 3,
    IncidentPriority.critical: 4,
}


def get_rule(
        detection: AIDetection,
) -> IncidentRule:
    return INCIDENT_RULES[detection.detection_type]


def is_production_camera_detection(
        detection: AIDetection,
) -> bool:
    if detection.is_test:
        return False

    if detection.source_type == DetectionSource.test:
        return False

    return detection.source_type == DetectionSource.camera


def priority_for_detection(
        detection: AIDetection,
        rule: IncidentRule,
) -> IncidentPriority:
    """
    AI confidence and incident priority are deliberately separate.

    The configured rule provides the normal incident priority.

    A trusted event-processing pipeline may optionally provide
    an incident_priority/severity hint in detection.attributes.
    Such a hint may only ESCALATE the configured priority.
    """

    base_priority = rule.priority

    attributes = detection.attributes or {}

    hint = (
            attributes.get("incident_priority")
            or attributes.get("severity")
    )

    if not isinstance(hint, str):
        return base_priority

    try:
        hinted_priority = IncidentPriority(
            hint.strip().lower()
        )
    except ValueError:
        return base_priority

    if (
            _PRIORITY_RANK[hinted_priority]
            > _PRIORITY_RANK[base_priority]
    ):
        return hinted_priority

    return base_priority


def humanize_detection_type(
        detection: AIDetection,
) -> str:
    return detection.detection_type.value.replace(
        "_",
        " ",
    ).title()


def incident_title(
        detection: AIDetection,
) -> str:
    return (
        f"AI Detected "
        f"{humanize_detection_type(detection)}"
    )


def incident_description(
        detection: AIDetection,
) -> str:
    confidence_percent = detection.confidence * 100

    camera = (
            detection.camera_identifier
            or "Unknown camera"
    )

    location = (
            detection.location_name
            or "Unknown location"
    )

    model = detection.model_name

    if detection.model_version:
        model = (
            f"{model} "
            f"{detection.model_version}"
        )

    return (
        f"Automatically generated from an MCC AI detection. "
        f"Detection type: "
        f"{humanize_detection_type(detection)}. "
        f"Confidence: {confidence_percent:.1f}%. "
        f"Camera: {camera}. "
        f"Location: {location}. "
        f"Model: {model}. "
        f"Detection UUID: {detection.detection_uuid}."
    )