from dataclasses import dataclass

from app.modules.ai_detections.models import DetectionType
from app.modules.incidents.models import IncidentPriority


@dataclass(frozen=True)
class IncidentRule:
    min_confidence: float
    dedup_seconds: int
    priority: IncidentPriority
    auto_create: bool = True


INCIDENT_RULES: dict[DetectionType, IncidentRule] = {
    DetectionType.noise_pollution: IncidentRule(
        min_confidence=0.80,
        dedup_seconds=300,
        priority=IncidentPriority.high,
    ),
    DetectionType.illegal_dumping: IncidentRule(
        min_confidence=0.75,
        dedup_seconds=300,
        priority=IncidentPriority.high,
    ),
    DetectionType.skip_overflow: IncidentRule(
        min_confidence=0.80,
        dedup_seconds=3600,
        priority=IncidentPriority.high,
    ),
    DetectionType.unauthorized_vending: IncidentRule(
        min_confidence=0.80,
        dedup_seconds=900,
        priority=IncidentPriority.high,
    ),
    DetectionType.street_cleaner_non_compliance: IncidentRule(
        min_confidence=0.80,
        dedup_seconds=1800,
        priority=IncidentPriority.high,
    ),
    DetectionType.public_urination: IncidentRule(
        min_confidence=0.85,
        dedup_seconds=180,
        priority=IncidentPriority.high,
    ),
    DetectionType.vehicle_smoke_emission: IncidentRule(
        min_confidence=0.80,
        dedup_seconds=300,
        priority=IncidentPriority.high,
    ),
    DetectionType.road_damage: IncidentRule(
        min_confidence=0.70,
        dedup_seconds=86400,
        priority=IncidentPriority.high,
    ),
    DetectionType.pothole: IncidentRule(
        min_confidence=0.70,
        dedup_seconds=86400,
        priority=IncidentPriority.high,
    ),
    DetectionType.other: IncidentRule(
        min_confidence=0.90,
        dedup_seconds=300,
        priority=IncidentPriority.medium,
        auto_create=False,
    ),
}