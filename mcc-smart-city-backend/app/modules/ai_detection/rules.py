from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Any


@dataclass
class RuleAssessment:
    rule: str
    title: str
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    evidence_classes: list[str] = field(default_factory=list)
    incident_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "title": self.title,
            "status": self.status,
            "confidence": round(max(0.0, min(self.confidence, 1.0)), 4),
            "reasons": self.reasons,
            "evidence_classes": self.evidence_classes,
            "incident_type": self.incident_type,
        }


def _center(det: dict) -> tuple[float, float]:
    box = det["bbox"]
    return ((box["x1"] + box["x2"]) / 2, (box["y1"] + box["y2"]) / 2)


def _diag(det: dict) -> float:
    box = det["bbox"]
    return hypot(box["width"], box["height"])


def _near(a: dict, b: dict, multiplier: float = 1.6) -> bool:
    ax, ay = _center(a)
    bx, by = _center(b)
    distance = hypot(ax - bx, ay - by)
    scale = max(_diag(a), _diag(b), 1.0)
    return distance <= scale * multiplier


def _best(detections: list[dict], class_name: str) -> list[dict]:
    return [d for d in detections if d["class_name"] == class_name]


def evaluate_image_rules(detections: list[dict]) -> list[dict]:
    assessments: list[RuleAssessment] = []

    persons = _best(detections, "person")
    waste = _best(detections, "trash") + _best(detections, "bag")
    cars = _best(detections, "car")
    smoke = _best(detections, "vehicle_smoke")
    potholes = _best(detections, "pothole")
    cracks = _best(detections, "road_crack")
    brooms = _best(detections, "broom")
    skips = _best(detections, "waste_skip")

    if potholes:
        conf = max(d["confidence"] for d in potholes)
        assessments.append(RuleAssessment(
            rule="pothole_detection",
            title="Possible pothole",
            status="candidate",
            confidence=conf,
            reasons=["Pothole class detected in the image."],
            evidence_classes=["pothole"],
            incident_type="pothole",
        ))

    if cracks:
        conf = max(d["confidence"] for d in cracks)
        assessments.append(RuleAssessment(
            rule="road_damage_detection",
            title="Possible road damage",
            status="candidate",
            confidence=conf,
            reasons=["Road-crack class detected in the image."],
            evidence_classes=["road_crack"],
            incident_type="road_damage",
        ))

    smoke_pairs = [
        (car, plume)
        for car in cars
        for plume in smoke
        if _near(car, plume, 1.8)
    ]
    if smoke_pairs:
        conf = max(min(a["confidence"], b["confidence"]) for a, b in smoke_pairs)
        assessments.append(RuleAssessment(
            rule="vehicle_smoke_emission",
            title="Possible vehicle smoke emission",
            status="candidate",
            confidence=conf,
            reasons=["Vehicle smoke is spatially close to a detected car."],
            evidence_classes=["car", "vehicle_smoke"],
            incident_type="vehicle_smoke_emission",
        ))

    dumping_pairs = [
        (person, item)
        for person in persons
        for item in waste
        if _near(person, item, 1.5)
    ]
    if dumping_pairs:
        conf = max(min(a["confidence"], b["confidence"]) for a, b in dumping_pairs)
        assessments.append(RuleAssessment(
            rule="illegal_dumping_static",
            title="Dumping interaction requires video confirmation",
            status="observation",
            confidence=conf,
            reasons=[
                "A person is close to trash or a bag.",
                "A single image cannot prove that the person deposited the object and left it behind.",
            ],
            evidence_classes=["person", "trash/bag"],
            incident_type="illegal_dumping",
        ))

    cleaner_pairs = [
        (person, broom)
        for person in persons
        for broom in brooms
        if _near(person, broom, 1.4)
    ]
    if cleaner_pairs:
        conf = max(min(a["confidence"], b["confidence"]) for a, b in cleaner_pairs)
        assessments.append(RuleAssessment(
            rule="cleaning_activity",
            title="Cleaning activity observed",
            status="observation",
            confidence=conf,
            reasons=["A person and broom are spatially associated."],
            evidence_classes=["person", "broom"],
            incident_type=None,
        ))

    overflow_pairs = [
        (skip, item)
        for skip in skips
        for item in waste
        if _near(skip, item, 1.25)
    ]
    if overflow_pairs:
        conf = max(min(a["confidence"], b["confidence"]) for a, b in overflow_pairs)
        assessments.append(RuleAssessment(
            rule="skip_overflow_visual",
            title="Possible waste accumulation around skip",
            status="candidate",
            confidence=conf,
            reasons=[
                "Trash or a bag is detected close to a waste skip.",
                "This is a test heuristic; a dedicated fill-level rule should confirm overflow before enforcement.",
            ],
            evidence_classes=["waste_skip", "trash/bag"],
            incident_type="skip_overflow",
        ))

    return [item.as_dict() for item in assessments]


class VideoRuleEngine:
    """Small test-lab temporal rule engine.

    It deliberately produces candidate events, not enforcement decisions.
    Production rules can later reuse the same event shape with camera/GIS context.
    """

    def __init__(self) -> None:
        self.frame_index = 0
        self.dumping_contact_seen = False
        self.dumping_departure_frames = 0
        self.smoke_frames = 0
        self.pothole_frames = 0
        self.road_damage_frames = 0
        self.cleaning_frames = 0
        self.skip_frames = 0
        self.events: dict[str, RuleAssessment] = {}

    def _store(self, assessment: RuleAssessment) -> None:
        previous = self.events.get(assessment.rule)
        if previous is None or assessment.confidence > previous.confidence:
            self.events[assessment.rule] = assessment

    def observe(self, detections: list[dict]) -> None:
        self.frame_index += 1

        persons = _best(detections, "person")
        waste = _best(detections, "trash") + _best(detections, "bag")
        cars = _best(detections, "car")
        smoke = _best(detections, "vehicle_smoke")
        potholes = _best(detections, "pothole")
        cracks = _best(detections, "road_crack")
        brooms = _best(detections, "broom")
        skips = _best(detections, "waste_skip")

        near_person_waste = any(_near(p, w, 1.5) for p in persons for w in waste)
        if near_person_waste:
            self.dumping_contact_seen = True
            self.dumping_departure_frames = 0
        elif self.dumping_contact_seen and waste:
            person_still_near = any(_near(p, w, 1.8) for p in persons for w in waste)
            if not person_still_near:
                self.dumping_departure_frames += 1
            else:
                self.dumping_departure_frames = 0

        if self.dumping_contact_seen and self.dumping_departure_frames >= 6:
            confs = [d["confidence"] for d in waste]
            conf = max(confs) if confs else 0.5
            self._store(RuleAssessment(
                rule="illegal_dumping_temporal",
                title="Possible illegal dumping event",
                status="candidate",
                confidence=conf,
                reasons=[
                    "A person was observed near a trash/bag object.",
                    "The waste object remained visible for several sampled frames after the person was no longer nearby.",
                ],
                evidence_classes=["person", "trash/bag"],
                incident_type="illegal_dumping",
            ))

        if any(_near(c, s, 1.8) for c in cars for s in smoke):
            self.smoke_frames += 1
        else:
            self.smoke_frames = max(0, self.smoke_frames - 1)
        if self.smoke_frames >= 3:
            conf = max([d["confidence"] for d in smoke] or [0.5])
            self._store(RuleAssessment(
                rule="vehicle_smoke_emission",
                title="Possible vehicle smoke emission",
                status="candidate",
                confidence=conf,
                reasons=["Vehicle smoke remained close to a car across multiple sampled frames."],
                evidence_classes=["car", "vehicle_smoke"],
                incident_type="vehicle_smoke_emission",
            ))

        self.pothole_frames = self.pothole_frames + 1 if potholes else max(0, self.pothole_frames - 1)
        if self.pothole_frames >= 3:
            self._store(RuleAssessment(
                rule="pothole_detection",
                title="Persistent pothole detection",
                status="candidate",
                confidence=max(d["confidence"] for d in potholes),
                reasons=["Pothole was detected across multiple sampled video frames."],
                evidence_classes=["pothole"],
                incident_type="pothole",
            ))

        self.road_damage_frames = self.road_damage_frames + 1 if cracks else max(0, self.road_damage_frames - 1)
        if self.road_damage_frames >= 3:
            self._store(RuleAssessment(
                rule="road_damage_detection",
                title="Persistent road-damage detection",
                status="candidate",
                confidence=max(d["confidence"] for d in cracks),
                reasons=["Road crack was detected across multiple sampled video frames."],
                evidence_classes=["road_crack"],
                incident_type="road_damage",
            ))

        if any(_near(p, b, 1.4) for p in persons for b in brooms):
            self.cleaning_frames += 1
        else:
            self.cleaning_frames = max(0, self.cleaning_frames - 1)
        if self.cleaning_frames >= 4:
            conf = max([d["confidence"] for d in brooms] or [0.5])
            self._store(RuleAssessment(
                rule="cleaning_activity",
                title="Cleaning activity observed",
                status="observation",
                confidence=conf,
                reasons=["Person and broom remained associated across multiple sampled frames."],
                evidence_classes=["person", "broom"],
            ))

        if any(_near(s, w, 1.25) for s in skips for w in waste):
            self.skip_frames += 1
        else:
            self.skip_frames = max(0, self.skip_frames - 1)
        if self.skip_frames >= 3:
            conf = max([d["confidence"] for d in skips + waste] or [0.5])
            self._store(RuleAssessment(
                rule="skip_overflow_visual",
                title="Possible waste accumulation around skip",
                status="candidate",
                confidence=conf,
                reasons=["Waste remained close to a waste skip across several sampled frames."],
                evidence_classes=["waste_skip", "trash/bag"],
                incident_type="skip_overflow",
            ))

    def results(self) -> list[dict]:
        return [item.as_dict() for item in self.events.values()]
