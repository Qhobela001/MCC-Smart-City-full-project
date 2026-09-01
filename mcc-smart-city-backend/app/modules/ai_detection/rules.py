from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import hypot
from statistics import mean
from typing import Any

from .associations import bbox_center, bbox_diagonal, build_associations, normalized_center_distance
from .cleanliness import assess_street_cleanliness, summarize_cleanliness_history
from .tracking import SimpleObjectTracker


@dataclass
class RuleAssessment:
    rule: str
    title: str
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    evidence_classes: list[str] = field(default_factory=list)
    incident_type: str | None = None
    related_track_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "title": self.title,
            "status": self.status,
            "confidence": round(max(0.0, min(float(self.confidence), 1.0)), 4),
            "reasons": self.reasons,
            "evidence_classes": self.evidence_classes,
            "incident_type": self.incident_type,
            "related_track_ids": sorted(set(self.related_track_ids)),
            "details": self.details,
        }


@dataclass
class Occurrence:
    occurrence_id: str
    occurrence_type: str
    title: str
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    evidence_classes: list[str] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)
    incident_type: str | None = None
    vehicle_track_id: str | None = None
    person_track_ids: list[str] = field(default_factory=list)
    waste_track_ids: list[str] = field(default_factory=list)
    plate_track_id: str | None = None
    plate_status: str | None = None
    follow_up: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "occurrence_type": self.occurrence_type,
            "title": self.title,
            "status": self.status,
            "confidence": round(max(0.0, min(float(self.confidence), 1.0)), 4),
            "reasons": self.reasons,
            "evidence_classes": sorted(set(self.evidence_classes)),
            "track_ids": sorted(set(filter(None, self.track_ids))),
            "incident_type": self.incident_type,
            "vehicle_track_id": self.vehicle_track_id,
            "person_track_ids": sorted(set(filter(None, self.person_track_ids))),
            "waste_track_ids": sorted(set(filter(None, self.waste_track_ids))),
            "plate_track_id": self.plate_track_id,
            "plate_status": self.plate_status,
            "follow_up": self.follow_up,
            "details": self.details,
        }


def _detections_of(detections: list[dict[str, Any]], *classes: str) -> list[tuple[int, dict[str, Any]]]:
    wanted = set(classes)
    return [
        (index, detection)
        for index, detection in enumerate(detections)
        if detection["class_name"] in wanted
    ]


def _associations_of(
    associations: list[dict[str, Any]],
    association_type: str,
) -> list[dict[str, Any]]:
    return [
        association
        for association in associations
        if association["association_type"] == association_type
    ]


def _association_confidence(association: dict[str, Any]) -> float:
    return float(association.get("confidence", 0.0))


def _find_plate_for_car(
    associations: list[dict[str, Any]],
    car_index: int,
) -> dict[str, Any] | None:
    matches = [
        item
        for item in _associations_of(associations, "car_plate")
        if int(item["left_index"]) == int(car_index)
    ]
    if not matches:
        return None
    return max(matches, key=_association_confidence)


def _find_vehicle_for_person(
    associations: list[dict[str, Any]],
    person_index: int,
) -> dict[str, Any] | None:
    matches = [
        item
        for item in _associations_of(associations, "person_car")
        if int(item["left_index"]) == int(person_index)
    ]
    if not matches:
        return None
    return max(matches, key=_association_confidence)


def evaluate_image_intelligence(
    detections: list[dict[str, Any]],
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    """Evaluate spatial/contextual intelligence for one still image.

    Still-image rules deliberately avoid claiming temporal events such as
    completed illegal dumping. They produce observations/candidates only.
    """

    associations = build_associations(detections)
    rules: list[RuleAssessment] = []
    occurrences: list[Occurrence] = []
    occurrence_counter: Counter[str] = Counter()

    def next_id(kind: str) -> str:
        occurrence_counter[kind] += 1
        return f"IMG-{kind.upper().replace('_', '-')}-{occurrence_counter[kind]}"

    # ------------------------------------------------------------
    # Vehicle emission: car + smoke + optional plate.
    # ------------------------------------------------------------
    for smoke_link in _associations_of(associations, "car_smoke"):
        car_index = int(smoke_link["left_index"])
        smoke_index = int(smoke_link["right_index"])
        car = detections[car_index]
        plume = detections[smoke_index]
        plate_link = _find_plate_for_car(associations, car_index)
        plate_index = int(plate_link["right_index"]) if plate_link else None
        plate = detections[plate_index] if plate_index is not None else None

        plate_status = "detected" if plate else "pending"
        follow_up = (
            "Plate detected. Preserve the best plate crop for OCR."
            if plate
            else "Registration pending. Preserve vehicle evidence so a downstream camera can provide a better plate view."
        )
        conf_values = [float(car["confidence"]), float(plume["confidence"])]
        if plate:
            conf_values.append(float(plate["confidence"]))
        confidence = min(conf_values[:2])

        occurrences.append(Occurrence(
            occurrence_id=next_id("vehicle_emission"),
            occurrence_type="vehicle_emission",
            title="Possible vehicle smoke emission",
            status="candidate",
            confidence=confidence,
            reasons=[
                "Vehicle smoke is spatially associated with a detected car.",
                "Video persistence is still required before an operational emission incident is created.",
            ],
            evidence_classes=["car", "vehicle_smoke"] + (["license_plate"] if plate else []),
            incident_type="vehicle_smoke_emission",
            plate_status=plate_status,
            follow_up=follow_up,
            details={
                "car_detection_index": car_index,
                "smoke_detection_index": smoke_index,
                "plate_detection_index": plate_index,
                "smoke_source": plume.get("source", "primary"),
                "ocr_status": "not_enabled",
            },
        ))
        rules.append(RuleAssessment(
            rule="vehicle_smoke_emission",
            title="Vehicle and smoke correlated",
            status="candidate",
            confidence=confidence,
            reasons=[
                "A smoke detection was associated with a car rather than treated as an isolated object.",
                f"License plate status: {plate_status}.",
            ],
            evidence_classes=["car", "vehicle_smoke"] + (["license_plate"] if plate else []),
            incident_type="vehicle_smoke_emission",
            details={"plate_status": plate_status},
        ))

    # Smoke without a vehicle is useful diagnostic information but not an event.
    linked_smoke_indices = {
        int(item["right_index"])
        for item in _associations_of(associations, "car_smoke")
    }
    unlinked_smoke = [
        index for index, _ in _detections_of(detections, "vehicle_smoke")
        if index not in linked_smoke_indices
    ]
    if unlinked_smoke:
        rules.append(RuleAssessment(
            rule="unassociated_vehicle_smoke",
            title="Smoke detected without a vehicle association",
            status="observation",
            confidence=max(float(detections[index]["confidence"]) for index in unlinked_smoke),
            reasons=["Visible smoke was detected, but it could not be reliably associated with a car in this frame."],
            evidence_classes=["vehicle_smoke"],
            details={"unlinked_smoke_detection_indices": unlinked_smoke},
        ))

    # ------------------------------------------------------------
    # Illegal dumping context: person/car + waste.
    # Number plates are deliberately NOT part of the dumping decision.
    # A still image can only establish context; deposition/abandonment
    # requires temporal video evidence.
    # ------------------------------------------------------------
    for dumping_link in _associations_of(associations, "person_waste"):
        person_index = int(dumping_link["left_index"])
        waste_index = int(dumping_link["right_index"])
        person = detections[person_index]
        waste = detections[waste_index]

        vehicle_link = _find_vehicle_for_person(associations, person_index)
        car_index = int(vehicle_link["right_index"]) if vehicle_link else None

        occurrences.append(Occurrence(
            occurrence_id=next_id("dumping_context"),
            occurrence_type="illegal_dumping_context",
            title="Waste-handling context requires video confirmation",
            status="observation",
            confidence=min(float(person["confidence"]), float(waste["confidence"])),
            reasons=[
                "A person is spatially associated with trash or a bag.",
                "A still image cannot prove that the object was deposited and abandoned.",
            ],
            evidence_classes=["person", waste["class_name"]] + (["car"] if car_index is not None else []),
            incident_type="illegal_dumping",
            follow_up="Use video tracking to confirm object movement, deposition, actor departure and waste persistence.",
            details={
                "person_detection_index": person_index,
                "waste_detection_index": waste_index,
                "vehicle_detection_index": car_index,
                "license_plate_used_for_decision": False,
            },
        ))
        rules.append(RuleAssessment(
            rule="illegal_dumping_static",
            title="Person and waste correlated",
            status="observation",
            confidence=min(float(person["confidence"]), float(waste["confidence"])),
            reasons=[
                "A person is close to trash or a bag.",
                "Video confirmation is required to determine whether that waste moved with the actor, was deposited, and remained after departure.",
            ],
            evidence_classes=["person", "trash/bag"],
            incident_type="illegal_dumping",
        ))

    # Vehicle-linked waste context where a person may be occluded.
    person_linked_waste = {
        int(item["right_index"])
        for item in _associations_of(associations, "person_waste")
    }
    for vehicle_waste_link in _associations_of(associations, "car_waste"):
        waste_index = int(vehicle_waste_link["right_index"])
        if waste_index in person_linked_waste:
            continue
        car_index = int(vehicle_waste_link["left_index"])
        car = detections[car_index]
        waste = detections[waste_index]
        occurrences.append(Occurrence(
            occurrence_id=next_id("vehicle_dumping_context"),
            occurrence_type="illegal_dumping_context",
            title="Vehicle and waste context requires video confirmation",
            status="observation",
            confidence=min(float(car["confidence"]), float(waste["confidence"])),
            reasons=[
                "Trash or a bag is spatially associated with a detected car.",
                "Video tracking is required to determine whether the waste originated near the vehicle, became stationary, and remained after the vehicle left.",
            ],
            evidence_classes=["car", waste["class_name"]],
            incident_type="illegal_dumping",
            vehicle_track_id=car.get("track_id"),
            follow_up="Track the vehicle and waste sequence. Registration/number-plate handling is a separate evidence-enrichment stage.",
            details={
                "vehicle_detection_index": car_index,
                "waste_detection_index": waste_index,
                "person_visible": False,
                "license_plate_used_for_decision": False,
            },
        ))

    # ------------------------------------------------------------
    # Cleaner activity: person + broom.
    # ------------------------------------------------------------
    cleaner_links = _associations_of(associations, "person_broom")
    for cleaner_link in cleaner_links:
        occurrences.append(Occurrence(
            occurrence_id=next_id("cleaning_activity"),
            occurrence_type="cleaning_activity",
            title="Cleaning activity context observed",
            status="observation",
            confidence=float(cleaner_link["confidence"]),
            reasons=["A person and broom are spatially associated."],
            evidence_classes=["person", "broom"],
            follow_up="Video, assigned-zone and before/after cleanliness context are required to assess cleaner performance.",
        ))
    if cleaner_links:
        rules.append(RuleAssessment(
            rule="cleaning_activity",
            title="Cleaning activity observed",
            status="observation",
            confidence=max(float(item["confidence"]) for item in cleaner_links),
            reasons=["Person and broom are spatially associated."],
            evidence_classes=["person", "broom"],
        ))

    # ------------------------------------------------------------
    # Waste skip state.
    # ------------------------------------------------------------
    concerning_skip_links = [
        item for item in _associations_of(associations, "waste_skip")
        if item["relation"] in {"around_skip", "above_skip"}
    ]
    if concerning_skip_links:
        confidence = max(float(item["confidence"]) for item in concerning_skip_links)
        occurrences.append(Occurrence(
            occurrence_id=next_id("waste_skip"),
            occurrence_type="waste_skip_monitoring",
            title="Waste accumulation around skip",
            status="candidate",
            confidence=confidence,
            reasons=[
                "Waste is located around or above a detected waste skip rather than clearly contained inside it.",
                "A dedicated fill-level/segmentation method can later improve overflow severity estimation.",
            ],
            evidence_classes=["waste_skip", "trash/bag"],
            incident_type="skip_overflow",
            details={
                "relations": [item["relation"] for item in concerning_skip_links],
            },
        ))
        rules.append(RuleAssessment(
            rule="skip_overflow_visual",
            title="Possible waste accumulation around skip",
            status="candidate",
            confidence=confidence,
            reasons=["Waste is spatially outside/above the normal skip containment area."],
            evidence_classes=["waste_skip", "trash/bag"],
            incident_type="skip_overflow",
        ))

    # ------------------------------------------------------------
    # Road damage: group potholes and cracks into a road condition.
    # ------------------------------------------------------------
    potholes = _detections_of(detections, "pothole")
    cracks = _detections_of(detections, "road_crack")
    if potholes or cracks:
        all_damage = potholes + cracks
        confidence = max(float(item[1]["confidence"]) for item in all_damage)
        classes = sorted({item[1]["class_name"] for item in all_damage})
        occurrences.append(Occurrence(
            occurrence_id=next_id("road_damage"),
            occurrence_type="road_damage",
            title="Possible road damage",
            status="candidate",
            confidence=confidence,
            reasons=[
                "Road-surface damage was detected in the visible road area.",
                "GIS and repeated observations should be used to group recurring detections at the same location.",
            ],
            evidence_classes=classes,
            incident_type="road_damage" if "road_crack" in classes else "pothole",
            details={
                "pothole_count": len(potholes),
                "road_crack_count": len(cracks),
                "grouped_damage_pairs": len(_associations_of(associations, "road_damage")),
            },
        ))
        rules.append(RuleAssessment(
            rule="road_damage_detection",
            title="Road damage detected",
            status="candidate",
            confidence=confidence,
            reasons=[f"Detected road-damage classes: {', '.join(classes)}."],
            evidence_classes=classes,
            incident_type="road_damage" if "road_crack" in classes else "pothole",
        ))

    street_cleanliness = assess_street_cleanliness(
        detections,
        image_width,
        image_height,
        associations,
    )
    if street_cleanliness["state"] in {"littered", "poor"}:
        rules.append(RuleAssessment(
            rule="street_cleanliness",
            title="Street cleanliness requires attention",
            status="observation",
            confidence=min(1.0, max(0.5, (100.0 - float(street_cleanliness["score"])) / 100.0 + 0.35)),
            reasons=list(street_cleanliness["reasons"]),
            evidence_classes=["trash", "bag", "waste_skip"],
            details={"cleanliness_score": street_cleanliness["score"], "state": street_cleanliness["state"]},
        ))

    return {
        "associations": associations,
        "rules": [rule.as_dict() for rule in rules],
        "occurrences": [occurrence.as_dict() for occurrence in occurrences],
        "street_cleanliness": street_cleanliness,
    }


class VideoRuleEngine:
    """Stateful Test Lab rule engine for sampled video frames.

    It correlates tracked detections into provisional occurrences. It does not
    create production incidents; the existing incident engine remains the later
    operational boundary after these rules are validated.
    """

    def __init__(
        self,
        *,
        smoke_window_seconds: float = 3.0,
        smoke_candidate_hits: int = 2,
        smoke_strong_hits: int = 3,
    ) -> None:
        self.sampled_frame_index = 0
        self.tracker = SimpleObjectTracker(max_misses=60)
        self.rules: dict[str, RuleAssessment] = {}
        self.occurrences: dict[str, Occurrence] = {}
        self.association_counts: Counter[str] = Counter()
        self.cleanliness_history: list[dict[str, Any]] = []

        # Smoke is visually unstable: one plume can disappear/reappear between
        # detections even though the real-world emission is continuous. Keep a
        # time-based evidence window instead of requiring smoke on every frame.
        self.smoke_window_seconds = max(0.5, float(smoke_window_seconds))
        self.smoke_candidate_hits = max(2, int(smoke_candidate_hits))
        self.smoke_strong_hits = max(self.smoke_candidate_hits + 1, int(smoke_strong_hits))

        # Illegal dumping is modeled as a waste-object lifecycle. A waste
        # track must first be linked to one plausible actor/vehicle, then show
        # evidence of movement/new appearance, become stationary, and remain
        # after that actor leaves. This prevents a person merely walking past
        # pre-existing rubbish from becoming a dumping event.
        self.dumping_state: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "contact_seen": False,
            "owner_kind": None,
            "owner_id": None,
            "owner_confidence": 0.0,
            "person_ids": set(),
            "vehicle_ids": set(),
            "max_confidence": 0.0,
            "direct_hits": 0,
            "inside_skip": False,
            "first_seen_seconds": None,
            "first_contact_seconds": None,
            "last_contact_seconds": None,
            "last_seen_seconds": None,
            "last_direct_seen_seconds": None,
            "last_center": None,
            "last_bbox_diagonal": None,
            "meaningful_motion_seen": False,
            "motion_since_contact": 0.0,
            "last_motion_seconds": None,
            "stationary_since_seconds": None,
            "new_near_actor": False,
            "deposited_seconds": None,
            "departure_started_seconds": None,
            "lifecycle_state": "observed",
            "last_seen": 0,
        })
        # Some real illegal-dumping objects are not represented by the current
        # YOLO waste classes (for example bicycles, furniture, appliances or
        # mixed debris). The model can occasionally label these as a weak,
        # short-lived waste_skip. We keep that raw class untouched, but allow
        # a small/transient skip-like detection to act as an UNCLASSIFIED
        # WASTE/DEBRIS candidate for dumping correlation only. A genuine skip
        # quickly accumulates repeated direct hits and therefore stops being
        # eligible for this fallback.
        self.transient_skip_hits: Counter[str] = Counter()
        self.transient_skip_first_seen: dict[str, float] = {}
        self.dumping_role_by_track: dict[str, str] = {}

        self.vehicle_emission_state: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "total_smoke_hits": 0,
            "temporal_smoke_hits": 0,
            "smoke_track_ids": set(),
            "plate_ids": set(),
            "max_confidence": 0.0,
            "last_seen": 0,
            "smoke_events": [],
            "strong_candidate_seen": False,
        })
        self.recent_vehicle_context: dict[str, dict[str, Any]] = {}
        self.cleaning_pair_hits: Counter[tuple[str, str]] = Counter()
        self.cleaning_pair_confidence: dict[tuple[str, str], float] = {}
        self.skip_state: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "concerning_hits": 0,
            "waste_ids": set(),
            "relations": set(),
            "max_confidence": 0.0,
        })
        self.road_track_hits: Counter[str] = Counter()
        self.road_track_confidence: dict[str, float] = {}
        self.road_pair_hits: Counter[tuple[str, str]] = Counter()

    def _store_rule(self, assessment: RuleAssessment) -> None:
        previous = self.rules.get(assessment.rule)
        if previous is None or assessment.confidence >= previous.confidence:
            self.rules[assessment.rule] = assessment

    def _upsert_occurrence(self, occurrence: Occurrence) -> None:
        previous = self.occurrences.get(occurrence.occurrence_id)
        if previous is None:
            self.occurrences[occurrence.occurrence_id] = occurrence
            return

        # Preserve the strongest/newest evidence when an occurrence evolves,
        # e.g. a plate becomes visible after the emission event already started.
        previous.confidence = max(previous.confidence, occurrence.confidence)
        status_rank = {"observation": 0, "candidate": 1, "confirmed": 2}
        if status_rank.get(occurrence.status, 0) >= status_rank.get(previous.status, 0):
            previous.title = occurrence.title
            previous.status = occurrence.status
            previous.incident_type = occurrence.incident_type or previous.incident_type
            if occurrence.follow_up:
                previous.follow_up = occurrence.follow_up
        previous.reasons = list(dict.fromkeys(previous.reasons + occurrence.reasons))
        previous.evidence_classes = list(dict.fromkeys(previous.evidence_classes + occurrence.evidence_classes))
        previous.track_ids = list(dict.fromkeys(previous.track_ids + occurrence.track_ids))
        previous.person_track_ids = list(dict.fromkeys(previous.person_track_ids + occurrence.person_track_ids))
        previous.waste_track_ids = list(dict.fromkeys(previous.waste_track_ids + occurrence.waste_track_ids))
        previous.vehicle_track_id = occurrence.vehicle_track_id or previous.vehicle_track_id
        previous.plate_track_id = occurrence.plate_track_id or previous.plate_track_id
        if occurrence.plate_status == "detected":
            previous.plate_status = "detected"
            previous.follow_up = occurrence.follow_up
        elif previous.plate_status is None:
            previous.plate_status = occurrence.plate_status
        previous.details.update(occurrence.details)

    @staticmethod
    def _track_id(detection: dict[str, Any]) -> str | None:
        value = detection.get("track_id")
        return str(value) if value else None

    def observe(
        self,
        detections: list[dict[str, Any]],
        image_width: int,
        image_height: int,
        *,
        time_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        self.sampled_frame_index += 1
        current_time = float(time_seconds) if time_seconds is not None else float(self.sampled_frame_index)
        # The tracker returns both fresh YOLO detections and short-gap predicted
        # boxes. Predicted boxes keep the overlay/track identity stable but are
        # never allowed to create new rule evidence on their own.
        detections = self.tracker.update(
            detections,
            self.sampled_frame_index,
            time_seconds=current_time,
            image_width=image_width,
            image_height=image_height,
        )
        observed_detections = [
            detection for detection in detections
            if not bool(detection.get("is_predicted"))
        ]

        # --------------------------------------------------------
        # Generic dumped-object fallback.
        # --------------------------------------------------------
        # The trained detector currently knows trash, bag and waste_skip, but
        # illegal dumping may involve furniture, bicycles, appliances, timber,
        # rubble or mixed debris. In the supplied CCTV examples the dumped
        # bicycle/debris is not classified as trash/bag, while a few weak
        # waste_skip hits appear on the newly deposited material. Treat ONLY a
        # small, low-hit skip-like track as unclassified waste/debris for the
        # dumping lifecycle. This does not alter the YOLO class and is never
        # used for skip-overflow logic.
        frame_area = max(float(image_width) * float(image_height), 1.0)
        for detection in observed_detections:
            if detection.get("class_name") != "waste_skip":
                continue
            track_id = self._track_id(detection)
            if not track_id:
                continue
            self.transient_skip_hits[track_id] += 1
            self.transient_skip_first_seen.setdefault(track_id, current_time)
            box = detection.get("bbox", {})
            area_ratio = (
                max(0.0, float(box.get("width", 0.0)))
                * max(0.0, float(box.get("height", 0.0)))
                / frame_area
            )
            direct_hits = int(self.transient_skip_hits[track_id])
            # Genuine skips should normally be repeatedly visible. The fallback
            # is intentionally conservative and only applies while the track is
            # sparse and relatively small in the frame.
            if direct_hits <= 12 and area_ratio <= 0.085:
                detection["dumping_role"] = "unclassified_waste_candidate"
                detection["original_class_name"] = "waste_skip"
                detection["dumping_role_reason"] = (
                    "Transient skip-like detection treated as generic waste/debris "
                    "for illegal-dumping correlation only."
                )
                self.dumping_role_by_track[track_id] = "unclassified_waste_candidate"
            elif direct_hits > 12:
                # A repeatedly visible skip-like object is much more likely to
                # be a real waste skip than arbitrary dumped debris.
                self.dumping_role_by_track.pop(track_id, None)

        # Propagate the provisional dumping role onto tracker-held copies so the
        # overlay and lifecycle keep the same interpretation during short YOLO
        # gaps. The role is still auxiliary evidence, not a new model class.
        for detection in detections:
            track_id = self._track_id(detection)
            role = self.dumping_role_by_track.get(track_id or "")
            if role:
                detection["dumping_role"] = role
                detection["original_class_name"] = detection.get("class_name")

        associations = build_associations(observed_detections)
        continuity_associations = build_associations(detections)
        for association in associations:
            self.association_counts[association["association_type"]] += 1

        cleanliness = assess_street_cleanliness(
            observed_detections,
            image_width,
            image_height,
            associations,
        )
        self.cleanliness_history.append(cleanliness)

        current_tracks = {
            self._track_id(detection): detection
            for detection in detections
            if self._track_id(detection)
        }

        # Keep a short memory of vehicle positions. Smoke can temporarily hide
        # a vehicle in the exact frame where the plume is easiest to detect.
        for detection in observed_detections:
            if detection["class_name"] != "car":
                continue
            car_id = self._track_id(detection)
            if not car_id:
                continue
            previous = self.recent_vehicle_context.get(car_id, {})
            self.recent_vehicle_context[car_id] = {
                "bbox": dict(detection["bbox"]),
                "last_seen": self.sampled_frame_index,
                "last_seen_seconds": current_time,
                "max_confidence": max(
                    float(previous.get("max_confidence", 0.0)),
                    float(detection["confidence"]),
                ),
                "plate_ids": set(previous.get("plate_ids", set())),
            }

        # --------------------------------------------------------
        # Vehicle-plate evidence is reusable across occurrences.
        # --------------------------------------------------------
        plate_by_car: dict[str, str] = {}
        for link in _associations_of(associations, "car_plate"):
            car_id = link.get("left_track_id")
            plate_id = link.get("right_track_id")
            if car_id and plate_id:
                car_id = str(car_id)
                plate_id = str(plate_id)
                plate_by_car[car_id] = plate_id
                if car_id in self.recent_vehicle_context:
                    self.recent_vehicle_context[car_id]["plate_ids"].add(plate_id)

        # --------------------------------------------------------
        # Vehicle emission temporal rule with a sliding evidence window.
        # --------------------------------------------------------
        car_smoke_links = list(_associations_of(associations, "car_smoke"))

        # If smoke is visible but the car disappears for a short period, use
        # the recent tracked vehicle position as temporal context. This handles
        # cases where dense smoke briefly obscures the vehicle itself.
        linked_smoke_ids = {
            str(link.get("right_track_id"))
            for link in car_smoke_links
            if link.get("right_track_id")
        }
        for smoke_index, smoke in _detections_of(observed_detections, "vehicle_smoke"):
            smoke_id = self._track_id(smoke)
            if smoke_id and smoke_id in linked_smoke_ids:
                continue

            candidates: list[tuple[float, str, dict[str, Any]]] = []
            for car_id, context in self.recent_vehicle_context.items():
                last_seen_seconds = float(context.get("last_seen_seconds", current_time))
                age_seconds = max(0.0, current_time - last_seen_seconds)
                # Keep recent vehicle context for most of the same smoke window,
                # but cap it to avoid associating smoke with a long-gone car.
                if age_seconds > min(self.smoke_window_seconds, 2.5):
                    continue
                synthetic_car = {"bbox": context["bbox"]}
                distance = normalized_center_distance(smoke, synthetic_car)
                if distance <= 2.10:
                    candidates.append((distance, car_id, context))

            if candidates:
                distance, car_id, context = min(candidates, key=lambda item: item[0])
                confidence = min(
                    float(smoke["confidence"]),
                    float(context.get("max_confidence", smoke["confidence"])),
                ) * 0.90
                car_smoke_links.append({
                    "association_type": "car_smoke",
                    "left_index": -1,
                    "left_class": "car",
                    "left_track_id": car_id,
                    "right_index": smoke_index,
                    "right_class": "vehicle_smoke",
                    "right_track_id": smoke_id,
                    "relation": "recent_vehicle_track",
                    "confidence": round(confidence, 4),
                    "metadata": {
                        "normalized_distance": round(distance, 3),
                        "vehicle_age_seconds": round(
                            max(0.0, current_time - float(context.get("last_seen_seconds", current_time))),
                            3,
                        ),
                    },
                })
                self.association_counts["car_smoke_temporal"] += 1

        # Multiple smoke boxes in one sampled frame must not inflate temporal
        # evidence. Keep only the strongest smoke association per vehicle/frame.
        best_smoke_link_by_car: dict[str, dict[str, Any]] = {}
        for link in car_smoke_links:
            car_id = link.get("left_track_id")
            if not car_id:
                continue
            car_id = str(car_id)
            previous = best_smoke_link_by_car.get(car_id)
            if previous is None or float(link.get("confidence", 0.0)) > float(previous.get("confidence", 0.0)):
                best_smoke_link_by_car[car_id] = link

        for car_id, link in best_smoke_link_by_car.items():
            smoke_id = link.get("right_track_id")
            state = self.vehicle_emission_state[car_id]
            state["total_smoke_hits"] += 1
            if link.get("relation") == "recent_vehicle_track":
                state["temporal_smoke_hits"] += 1
            state["last_seen"] = self.sampled_frame_index
            state["max_confidence"] = max(state["max_confidence"], float(link["confidence"]))
            if smoke_id:
                state["smoke_track_ids"].add(str(smoke_id))
            if car_id in plate_by_car:
                state["plate_ids"].add(plate_by_car[car_id])
            if car_id in self.recent_vehicle_context:
                state["plate_ids"].update(self.recent_vehicle_context[car_id].get("plate_ids", set()))

            state["smoke_events"].append({
                "sampled_frame": self.sampled_frame_index,
                "time_seconds": current_time,
                "confidence": float(link["confidence"]),
                "temporal_vehicle_context": link.get("relation") == "recent_vehicle_track",
                "smoke_track_id": str(smoke_id) if smoke_id else None,
            })

            # Sliding window: old smoke evidence expires, but a candidate that
            # was already produced remains in the final Test Lab results.
            state["smoke_events"] = [
                event
                for event in state["smoke_events"]
                if current_time - float(event["time_seconds"]) <= self.smoke_window_seconds
            ]
            window_events = state["smoke_events"]
            window_hits = len(window_events)
            first_time = float(window_events[0]["time_seconds"]) if window_events else current_time
            last_time = float(window_events[-1]["time_seconds"]) if window_events else current_time
            span_seconds = max(0.0, last_time - first_time)

            plate_id = sorted(state["plate_ids"])[0] if state["plate_ids"] else None
            plate_status = "detected" if plate_id else "pending"
            related = [car_id] + sorted(state["smoke_track_ids"]) + ([plate_id] if plate_id else [])

            # One hit is kept as an observation only. It must not become an
            # enforcement candidate by itself.
            if window_hits == 1:
                observation_reasons = [
                    "One direct YOLO smoke observation was associated with this tracked vehicle.",
                    f"The rule keeps a {self.smoke_window_seconds:.1f}s evidence window open for additional direct smoke detections.",
                    "Tracker-held smoke rectangles may stay visible between detections, but predicted boxes do not count as extra smoke evidence.",
                    "A single smoke hit is not enough to create an enforcement candidate.",
                ]
                observation_follow_up = (
                    "Plate detected in this video. Preserve the best plate crop while waiting for more smoke evidence."
                    if plate_id
                    else "Registration pending. Keep the vehicle track active while waiting for more smoke evidence."
                )
                self._upsert_occurrence(Occurrence(
                    occurrence_id=f"VEHICLE-EMISSION-{car_id}",
                    occurrence_type="vehicle_emission",
                    title="Vehicle smoke observation",
                    status="observation",
                    confidence=float(state["max_confidence"]),
                    reasons=observation_reasons,
                    evidence_classes=["car", "vehicle_smoke"] + (["license_plate"] if plate_id else []),
                    track_ids=related,
                    vehicle_track_id=car_id,
                    plate_track_id=plate_id,
                    plate_status=plate_status,
                    incident_type=None,
                    follow_up=observation_follow_up,
                    details={
                        "evidence_strength": "single_observation",
                        "smoke_window_hits": window_hits,
                        "smoke_window_seconds": self.smoke_window_seconds,
                        "total_smoke_hits": state["total_smoke_hits"],
                        "direct_model_hits": 1,
                        "candidate_required_hits": self.smoke_candidate_hits,
                        "cross_camera_correlation_required": not bool(plate_id),
                    },
                ))
                self._store_rule(RuleAssessment(
                    rule=f"vehicle_smoke_evidence:{car_id}",
                    title="Vehicle smoke observed on a tracked car",
                    status="observation",
                    confidence=float(state["max_confidence"]),
                    reasons=observation_reasons,
                    evidence_classes=["car", "vehicle_smoke"] + (["license_plate"] if plate_id else []),
                    related_track_ids=related,
                    details={
                        "vehicle_track_id": car_id,
                        "plate_status": plate_status,
                        "evidence_strength": "single_observation",
                        "smoke_window_hits": window_hits,
                        "smoke_window_seconds": self.smoke_window_seconds,
                        "total_smoke_hits": state["total_smoke_hits"],
                    },
                ))

            if window_hits >= self.smoke_candidate_hits:
                strong = window_hits >= self.smoke_strong_hits and span_seconds >= 1.0
                if strong:
                    state["strong_candidate_seen"] = True
                evidence_strength = "strong" if strong else "candidate"
                title = (
                    "Strong vehicle smoke emission candidate"
                    if strong
                    else "Possible vehicle smoke emission"
                )
                follow_up = (
                    "Plate detected in this video. Preserve the best plate crop for OCR."
                    if plate_id
                    else "Registration pending. Preserve the vehicle track for downstream-camera correlation."
                )
                occurrence = Occurrence(
                    occurrence_id=f"VEHICLE-EMISSION-{car_id}",
                    occurrence_type="vehicle_emission",
                    title=title,
                    status="candidate",
                    confidence=float(state["max_confidence"]),
                    reasons=[
                        f"{window_hits} smoke observation(s) were associated with the same tracked car inside a {self.smoke_window_seconds:.1f}s sliding window.",
                        "Smoke does not need to be detected on every sampled frame; intermittent detections can support one continuous real-world emission event.",
                    ] + ([
                        f"The smoke observations span {span_seconds:.2f}s inside the active evidence window."
                    ] if span_seconds > 0 else []) + ([
                        f"{state['temporal_smoke_hits']} smoke observation(s) used recent vehicle-track context because the car was temporarily not detected in the exact smoke frame."
                    ] if state["temporal_smoke_hits"] else []),
                    evidence_classes=["car", "vehicle_smoke"] + (["license_plate"] if plate_id else []),
                    track_ids=related,
                    vehicle_track_id=car_id,
                    plate_track_id=plate_id,
                    plate_status=plate_status,
                    incident_type="vehicle_smoke_emission",
                    follow_up=follow_up,
                    details={
                        "evidence_strength": evidence_strength,
                        "smoke_window_hits": window_hits,
                        "smoke_window_seconds": self.smoke_window_seconds,
                        "smoke_window_span_seconds": round(span_seconds, 3),
                        "total_smoke_hits": state["total_smoke_hits"],
                        "temporal_smoke_hits": state["temporal_smoke_hits"],
                        "smoke_track_ids": sorted(state["smoke_track_ids"]),
                        "first_smoke_time_seconds": round(first_time, 3),
                        "last_smoke_time_seconds": round(last_time, 3),
                        "ocr_status": "not_enabled",
                        "cross_camera_correlation_required": not bool(plate_id),
                    },
                )
                self._upsert_occurrence(occurrence)
                self._store_rule(RuleAssessment(
                    rule=f"vehicle_smoke_evidence:{car_id}",
                    title=title,
                    status="candidate",
                    confidence=float(state["max_confidence"]),
                    reasons=occurrence.reasons,
                    evidence_classes=occurrence.evidence_classes,
                    incident_type="vehicle_smoke_emission",
                    related_track_ids=related,
                    details={
                        "plate_status": plate_status,
                        "vehicle_track_id": car_id,
                        "evidence_strength": evidence_strength,
                        "smoke_window_hits": window_hits,
                        "smoke_window_seconds": self.smoke_window_seconds,
                    },
                ))

        # Expire old evidence windows for cars that did not receive a smoke hit
        # on this sampled frame. We deliberately do not decrement counters.
        # This makes the rule time-based rather than frame-count based.
        for state in self.vehicle_emission_state.values():
            state["smoke_events"] = [
                event
                for event in state["smoke_events"]
                if current_time - float(event["time_seconds"]) <= self.smoke_window_seconds
            ]

        # --------------------------------------------------------
        # Illegal dumping temporal rule.
        #
        # Number plates are intentionally excluded from the decision.
        # The rule follows the WASTE lifecycle instead:
        #   observed -> associated -> carried/moved -> deposited -> abandoned
        # A candidate requires direct waste evidence after deposition; tracker
        # predictions preserve continuity but never manufacture fresh evidence.
        # --------------------------------------------------------
        person_vehicle: dict[str, str] = {}
        for link in _associations_of(associations, "person_car"):
            person_id = link.get("left_track_id")
            car_id = link.get("right_track_id")
            if person_id and car_id:
                person_vehicle[str(person_id)] = str(car_id)

        waste_skip_relation: dict[str, str] = {}
        for link in _associations_of(associations, "waste_skip"):
            waste_id = link.get("right_track_id")
            if waste_id:
                waste_skip_relation[str(waste_id)] = str(link["relation"])

        # Candidate actor links are grouped by waste and then reduced to ONE
        # primary owner. This avoids linking the same waste object to every
        # person in a crowded frame. Existing ownership receives a continuity
        # bonus so the association does not jump between nearby people/cars.
        actor_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for association_type, actor_kind in (("person_waste", "person"), ("car_waste", "car")):
            for link in _associations_of(associations, association_type):
                actor_id = link.get("left_track_id")
                waste_id = link.get("right_track_id")
                if not actor_id or not waste_id:
                    continue
                waste_id = str(waste_id)
                distance = float(link.get("metadata", {}).get("normalized_distance", 1.5))
                base = max(0.0, 1.8 - distance) + 0.35 * float(link.get("confidence", 0.0))
                state = self.dumping_state[waste_id]
                if state.get("owner_id") == str(actor_id) and state.get("owner_kind") == actor_kind:
                    base += 0.45
                # Prefer a directly visible person when person and vehicle are
                # almost equally plausible; vehicle ownership still wins when
                # no person is detected or the car is clearly closer.
                if actor_kind == "person":
                    base += 0.08
                actor_candidates[waste_id].append({
                    "actor_kind": actor_kind,
                    "actor_id": str(actor_id),
                    "score": base,
                    "confidence": float(link.get("confidence", 0.0)),
                    "distance": distance,
                })

        # Generic debris may become visible just after a vehicle starts moving
        # away. If no same-frame actor link exists, allow a short recent-car
        # association so vehicle dumping is not lost merely because the object
        # appeared one or two sampled frames later.
        for detection in observed_detections:
            if detection.get("dumping_role") != "unclassified_waste_candidate":
                continue
            waste_id = self._track_id(detection)
            if not waste_id or actor_candidates.get(waste_id):
                continue
            recent_candidates: list[tuple[float, str, dict[str, Any]]] = []
            for car_id, context in self.recent_vehicle_context.items():
                age_seconds = max(0.0, current_time - float(context.get("last_seen_seconds", current_time)))
                if age_seconds > 2.75:
                    continue
                synthetic_car = {"bbox": context["bbox"]}
                distance = normalized_center_distance(detection, synthetic_car)
                if distance <= 2.10:
                    recent_candidates.append((distance, str(car_id), context))
            if recent_candidates:
                distance, car_id, context = min(recent_candidates, key=lambda item: item[0])
                actor_candidates[waste_id].append({
                    "actor_kind": "car",
                    "actor_id": car_id,
                    "score": max(0.1, 1.65 - distance) + 0.20,
                    "confidence": min(float(detection.get("confidence", 0.25)), float(context.get("max_confidence", 0.25))),
                    "distance": distance,
                    "temporal_actor_context": True,
                })
                self.association_counts["car_waste_temporal"] += 1

        best_actor_for_waste: dict[str, dict[str, Any]] = {}
        for waste_id, candidates in actor_candidates.items():
            best_actor_for_waste[waste_id] = max(candidates, key=lambda item: item["score"])

        # Predicted boxes may preserve contact through a short YOLO gap, but
        # they never establish first contact or motion/deposition evidence.
        continuity_owner_contact: set[tuple[str, str]] = set()
        for association_type, actor_kind in (("person_waste", "person"), ("car_waste", "car")):
            for link in _associations_of(continuity_associations, association_type):
                actor_id = link.get("left_track_id")
                waste_id = link.get("right_track_id")
                if actor_id and waste_id:
                    continuity_owner_contact.add((str(actor_id), str(waste_id)))

        direct_waste: dict[str, dict[str, Any]] = {}
        for detection in observed_detections:
            is_primary_waste = detection["class_name"] in {"trash", "bag"}
            is_generic_waste = detection.get("dumping_role") == "unclassified_waste_candidate"
            if not (is_primary_waste or is_generic_waste):
                continue
            waste_id = self._track_id(detection)
            if waste_id:
                direct_waste[waste_id] = detection

        # First update motion and direct-visibility evidence for every waste
        # object that YOLO actually sees in this sampled frame.
        frame_diagonal = max(hypot(float(image_width), float(image_height)), 1.0)
        for waste_id, waste in direct_waste.items():
            state = self.dumping_state[waste_id]
            state["last_seen"] = self.sampled_frame_index
            state["last_seen_seconds"] = current_time
            state["last_direct_seen_seconds"] = current_time
            state["direct_hits"] = int(state.get("direct_hits", 0)) + 1
            state["max_confidence"] = max(state["max_confidence"], float(waste["confidence"]))
            if state["first_seen_seconds"] is None:
                state["first_seen_seconds"] = current_time
            state["source_class"] = str(waste.get("class_name", "unknown"))
            state["dumping_role"] = waste.get("dumping_role")

            relation = waste_skip_relation.get(waste_id)
            if relation == "inside_skip":
                state["inside_skip"] = True
            elif relation in {"around_skip", "above_skip"}:
                state["inside_skip"] = False

            center = bbox_center(waste)
            diagonal = max(bbox_diagonal(waste), 1.0)
            previous_center = state.get("last_center")
            previous_diagonal = max(float(state.get("last_bbox_diagonal") or diagonal), 1.0)
            movement_object = 0.0
            movement_scene = 0.0
            if previous_center is not None:
                dx = float(center[0]) - float(previous_center[0])
                dy = float(center[1]) - float(previous_center[1])
                movement_px = hypot(dx, dy)
                movement_object = movement_px / max(diagonal, previous_diagonal, 1.0)
                movement_scene = movement_px / frame_diagonal

            state["last_center"] = center
            state["last_bbox_diagonal"] = diagonal

            meaningful_motion = movement_object >= 0.16 or movement_scene >= 0.006
            stationary = movement_object <= 0.075 and movement_scene <= 0.0035

            if meaningful_motion:
                state["last_motion_seconds"] = current_time
                state["stationary_since_seconds"] = None
                if state["contact_seen"]:
                    state["meaningful_motion_seen"] = True
                    state["motion_since_contact"] += movement_object
                    state["lifecycle_state"] = "carried_or_moving"
            elif stationary:
                if state["stationary_since_seconds"] is None:
                    state["stationary_since_seconds"] = current_time

        # Tracker-held waste/debris boxes can bridge short YOLO gaps after at
        # least two direct observations. They may support continuity and the
        # departure timer, but they never increment direct evidence counts.
        lifecycle_waste: dict[str, dict[str, Any]] = dict(direct_waste)
        for detection in detections:
            if not bool(detection.get("is_predicted")):
                continue
            is_primary_waste = detection.get("class_name") in {"trash", "bag"}
            is_generic_waste = detection.get("dumping_role") == "unclassified_waste_candidate"
            if not (is_primary_waste or is_generic_waste):
                continue
            waste_id = self._track_id(detection)
            if not waste_id or waste_id in lifecycle_waste:
                continue
            state = self.dumping_state.get(waste_id)
            if state and int(state.get("direct_hits", 0)) >= 2:
                lifecycle_waste[waste_id] = detection

        # Establish/update exclusive ownership only from DIRECT detections.
        for waste_id, candidate in best_actor_for_waste.items():
            state = self.dumping_state[waste_id]
            if waste_id not in direct_waste:
                continue
            actor_id = str(candidate["actor_id"])
            actor_kind = str(candidate["actor_kind"])
            old_owner = state.get("owner_id")
            old_last_contact = state.get("last_contact_seconds")
            owner_stale = (
                old_owner is None
                or old_last_contact is None
                or current_time - float(old_last_contact) > 1.5
            )
            if old_owner is None or old_owner == actor_id or owner_stale or candidate["score"] > float(state.get("owner_confidence", 0.0)) + 0.35:
                state["owner_id"] = actor_id
                state["owner_kind"] = actor_kind
                state["owner_confidence"] = float(candidate["score"])

            # Only the chosen owner establishes contact.
            if state.get("owner_id") != actor_id or state.get("owner_kind") != actor_kind:
                continue

            state["contact_seen"] = True
            state["last_contact_seconds"] = current_time
            if state["first_contact_seconds"] is None:
                state["first_contact_seconds"] = current_time
            first_seen_value = state.get("first_seen_seconds")
            first_seen = current_time if first_seen_value is None else float(first_seen_value)
            if current_time - first_seen <= 1.25:
                state["new_near_actor"] = True
            if state["lifecycle_state"] == "observed":
                state["lifecycle_state"] = "associated"

            if actor_kind == "person":
                state["person_ids"].add(actor_id)
                vehicle_id = person_vehicle.get(actor_id)
                if vehicle_id:
                    state["vehicle_ids"].add(vehicle_id)
            else:
                state["vehicle_ids"].add(actor_id)
            state["max_confidence"] = max(state["max_confidence"], float(candidate["confidence"]))

        # Evaluate deposition and abandonment. Direct detections are preferred;
        # short tracker-held continuity is allowed only after repeated direct
        # evidence as described above.
        for waste_id, waste in lifecycle_waste.items():
            state = self.dumping_state[waste_id]
            if not state["contact_seen"] or state["inside_skip"]:
                continue

            owner_id = state.get("owner_id")
            owner_kind = state.get("owner_kind")
            direct_contact_now = bool(
                waste_id in best_actor_for_waste
                and best_actor_for_waste[waste_id].get("actor_id") == owner_id
                and best_actor_for_waste[waste_id].get("actor_kind") == owner_kind
            )
            continuity_contact_now = bool(owner_id and (str(owner_id), waste_id) in continuity_owner_contact)

            stationary_since = state.get("stationary_since_seconds")
            stationary_seconds = (
                max(0.0, current_time - float(stationary_since))
                if stationary_since is not None else 0.0
            )
            is_generic_debris = state.get("dumping_role") == "unclassified_waste_candidate"
            has_deposition_origin = bool(
                state["meaningful_motion_seen"]
                or state["new_near_actor"]
                or (is_generic_debris and int(state.get("direct_hits", 0)) >= 2)
            )

            # A deposit is a waste object that had a plausible actor/vehicle
            # origin, is no longer in direct contact, and has become stationary.
            # For generic debris, two or more direct observations plus short
            # tracker continuity may bridge a detector gap after the actor leaves.
            generic_continuity_deposit = bool(
                is_generic_debris
                and int(state.get("direct_hits", 0)) >= 2
                and state.get("last_contact_seconds") is not None
                and current_time - float(state["last_contact_seconds"]) >= 0.75
                and state.get("last_direct_seen_seconds") is not None
                and current_time - float(state["last_direct_seen_seconds"]) <= 4.0
            )
            if (
                state["deposited_seconds"] is None
                and has_deposition_origin
                and not direct_contact_now
                and not continuity_contact_now
                and (stationary_seconds >= 0.75 or generic_continuity_deposit)
            ):
                state["deposited_seconds"] = current_time
                state["lifecycle_state"] = "deposited"

            if state["deposited_seconds"] is None:
                # Keep an observation visible in the Test Lab once a meaningful
                # actor/waste sequence has started, without calling it dumping.
                if has_deposition_origin:
                    person_ids = sorted(state["person_ids"])
                    vehicle_id = sorted(state["vehicle_ids"])[0] if state["vehicle_ids"] else None
                    related = person_ids + [waste_id] + ([vehicle_id] if vehicle_id else [])
                    self._upsert_occurrence(Occurrence(
                        occurrence_id=f"ILLEGAL-DUMPING-{waste_id}",
                        occurrence_type="illegal_dumping",
                        title="Waste movement under dumping review",
                        status="observation",
                        confidence=max(0.25, float(state["max_confidence"])),
                        reasons=[
                            "A waste track has been associated with one primary person/vehicle.",
                            "The rule is waiting for a stationary deposit followed by actor/vehicle departure.",
                        ],
                        evidence_classes=(["person"] if person_ids else []) + (["car"] if vehicle_id else []) + ["trash/bag"],
                        track_ids=related,
                        person_track_ids=person_ids,
                        waste_track_ids=[waste_id],
                        vehicle_track_id=vehicle_id,
                        incident_type="illegal_dumping",
                        follow_up="Continue tracking. Number plates are not used to decide whether dumping occurred.",
                        details={
                            "waste_state": state["lifecycle_state"],
                            "primary_actor_track_id": owner_id,
                            "primary_actor_kind": owner_kind,
                            "motion_since_contact": round(float(state["motion_since_contact"]), 3),
                            "direct_waste_hits": int(state.get("direct_hits", 0)),
                            "waste_role": state.get("dumping_role") or "model_waste_class",
                            "license_plate_used_for_decision": False,
                        },
                    ))
                continue

            # Determine whether the chosen actor has actually left the local
            # deposit area. A temporary YOLO miss is not enough: predicted
            # tracks in current_tracks still count as present.
            owner_far_or_absent = True
            if owner_id and owner_id in current_tracks:
                owner_detection = current_tracks[owner_id]
                owner_distance = normalized_center_distance(waste, owner_detection)
                owner_far_or_absent = owner_distance > 1.85

            if owner_far_or_absent and not direct_contact_now and not continuity_contact_now:
                if state["departure_started_seconds"] is None:
                    state["departure_started_seconds"] = current_time
            else:
                state["departure_started_seconds"] = None

            departure_seconds = (
                max(0.0, current_time - float(state["departure_started_seconds"]))
                if state["departure_started_seconds"] is not None else 0.0
            )
            deposit_persistence = max(0.0, current_time - float(state["deposited_seconds"]))

            person_ids = sorted(state["person_ids"])
            vehicle_id = sorted(state["vehicle_ids"])[0] if state["vehicle_ids"] else None
            related = person_ids + [waste_id] + ([vehicle_id] if vehicle_id else [])

            if departure_seconds < 1.25 or deposit_persistence < 1.25:
                self._upsert_occurrence(Occurrence(
                    occurrence_id=f"ILLEGAL-DUMPING-{waste_id}",
                    occurrence_type="illegal_dumping",
                    title="Waste deposited - monitoring actor departure",
                    status="observation",
                    confidence=max(0.35, float(state["max_confidence"])),
                    reasons=[
                        "The tracked waste object became stationary after actor/vehicle association.",
                        "The rule is waiting for the actor/vehicle to move away while the waste remains directly visible.",
                    ],
                    evidence_classes=(["person"] if person_ids else []) + (["car"] if vehicle_id else []) + ["trash/bag"],
                    track_ids=related,
                    person_track_ids=person_ids,
                    waste_track_ids=[waste_id],
                    vehicle_track_id=vehicle_id,
                    incident_type="illegal_dumping",
                    follow_up="Keep the before/deposit/after frames as provisional evidence. Plate/OCR is a separate later enrichment step.",
                    details={
                        "waste_state": "deposited",
                        "deposited_at_seconds": round(float(state["deposited_seconds"]), 3),
                        "deposit_persistence_seconds": round(deposit_persistence, 3),
                        "actor_departure_seconds": round(departure_seconds, 3),
                        "primary_actor_track_id": owner_id,
                        "primary_actor_kind": owner_kind,
                        "license_plate_used_for_decision": False,
                    },
                ))
                continue

            state["lifecycle_state"] = "abandoned"
            if person_ids:
                dumping_reasons = [
                    "A tracked waste object was linked to one primary person and showed movement/new appearance near that actor.",
                    "The waste then became stationary and remained directly visible after the person moved away.",
                ]
            else:
                dumping_reasons = [
                    "A tracked waste/debris object was linked to one primary vehicle and showed movement/new appearance near that vehicle.",
                    "The object then became stationary/persistent and remained tracked after the vehicle moved away.",
                ]

            occurrence = Occurrence(
                occurrence_id=f"ILLEGAL-DUMPING-{waste_id}",
                occurrence_type="illegal_dumping",
                title="Possible illegal dumping event",
                status="candidate",
                confidence=max(0.5, float(state["max_confidence"])),
                reasons=dumping_reasons,
                evidence_classes=(["person"] if person_ids else []) + (["car"] if vehicle_id else []) + ["trash/bag"],
                track_ids=related,
                person_track_ids=person_ids,
                waste_track_ids=[waste_id],
                vehicle_track_id=vehicle_id,
                incident_type="illegal_dumping",
                follow_up="Preserve the actor/vehicle, moving-waste, deposit and after-departure frames. Number plate handling remains separate from event classification.",
                details={
                    "waste_state": "abandoned",
                    "deposited_at_seconds": round(float(state["deposited_seconds"]), 3),
                    "deposit_persistence_seconds": round(deposit_persistence, 3),
                    "actor_departure_seconds": round(departure_seconds, 3),
                    "primary_actor_track_id": owner_id,
                    "primary_actor_kind": owner_kind,
                    "motion_since_contact": round(float(state["motion_since_contact"]), 3),
                    "disposed_inside_skip": False,
                    "event_time_seconds": round(current_time, 3),
                    "waste_source_class": state.get("source_class"),
                    "waste_role": state.get("dumping_role") or "model_waste_class",
                    "license_plate_used_for_decision": False,
                },
            )
            self._upsert_occurrence(occurrence)
            self._store_rule(RuleAssessment(
                rule=f"illegal_dumping:{waste_id}",
                title="Waste deposited and remained after actor departure",
                status="candidate",
                confidence=occurrence.confidence,
                reasons=occurrence.reasons,
                evidence_classes=occurrence.evidence_classes,
                incident_type="illegal_dumping",
                related_track_ids=related,
                details={
                    "waste_state": "abandoned",
                    "primary_actor_track_id": owner_id,
                    "primary_actor_kind": owner_kind,
                    "license_plate_used_for_decision": False,
                },
            ))

        # Expose the lifecycle on the returned detections so the Test Lab can
        # show exactly what the rule engine currently believes.
        actor_to_waste: dict[str, list[str]] = defaultdict(list)
        for waste_id, state in self.dumping_state.items():
            owner_id = state.get("owner_id")
            if owner_id:
                actor_to_waste[str(owner_id)].append(str(waste_id))

        for detection in detections:
            track_id = self._track_id(detection)
            if not track_id:
                continue
            if detection["class_name"] in {"trash", "bag"} or detection.get("dumping_role") == "unclassified_waste_candidate":
                state = self.dumping_state.get(track_id)
                if state:
                    detection["waste_state"] = state.get("lifecycle_state", "observed")
                    detection["associated_actor_track_id"] = state.get("owner_id")
                    detection["associated_actor_kind"] = state.get("owner_kind")
            elif track_id in actor_to_waste:
                detection["associated_waste_track_ids"] = sorted(set(actor_to_waste[track_id]))

        # --------------------------------------------------------
        # Cleaner activity.
        # --------------------------------------------------------
        for link in _associations_of(associations, "person_broom"):
            person_id = link.get("left_track_id")
            broom_id = link.get("right_track_id")
            if not person_id or not broom_id:
                continue
            key = (str(person_id), str(broom_id))
            self.cleaning_pair_hits[key] += 1
            self.cleaning_pair_confidence[key] = max(
                self.cleaning_pair_confidence.get(key, 0.0),
                float(link["confidence"]),
            )
            if self.cleaning_pair_hits[key] >= 4:
                occurrence = Occurrence(
                    occurrence_id=f"CLEANING-{key[0]}-{key[1]}",
                    occurrence_type="cleaning_activity",
                    title="Cleaning activity observed",
                    status="observation",
                    confidence=self.cleaning_pair_confidence[key],
                    reasons=[
                        "The same tracked person and broom remained associated across multiple sampled frames.",
                        "Cleaner performance must additionally use assignment/time context and before/after street cleanliness.",
                    ],
                    evidence_classes=["person", "broom"],
                    track_ids=[key[0], key[1]],
                    person_track_ids=[key[0]],
                    follow_up="Compare street cleanliness before and after this activity and later add assigned-zone/schedule context.",
                    details={"association_hits": self.cleaning_pair_hits[key]},
                )
                self._upsert_occurrence(occurrence)
                self._store_rule(RuleAssessment(
                    rule=f"cleaning_activity:{key[0]}",
                    title="Persistent person-broom cleaning activity",
                    status="observation",
                    confidence=occurrence.confidence,
                    reasons=occurrence.reasons,
                    evidence_classes=["person", "broom"],
                    related_track_ids=[key[0], key[1]],
                ))

        # --------------------------------------------------------
        # Waste-skip monitoring.
        # --------------------------------------------------------
        for link in _associations_of(associations, "waste_skip"):
            skip_id = link.get("left_track_id")
            waste_id = link.get("right_track_id")
            if not skip_id or not waste_id:
                continue
            relation = str(link["relation"])
            if relation not in {"around_skip", "above_skip"}:
                continue
            state = self.skip_state[str(skip_id)]
            state["concerning_hits"] += 1
            state["waste_ids"].add(str(waste_id))
            state["relations"].add(relation)
            state["max_confidence"] = max(state["max_confidence"], float(link["confidence"]))

            if state["concerning_hits"] >= 3:
                track_ids = [str(skip_id)] + sorted(state["waste_ids"])
                occurrence = Occurrence(
                    occurrence_id=f"WASTE-SKIP-{skip_id}",
                    occurrence_type="waste_skip_monitoring",
                    title="Persistent waste accumulation around skip",
                    status="candidate",
                    confidence=float(state["max_confidence"]),
                    reasons=[
                        "Waste remained around/above the same tracked waste skip across multiple sampled frames.",
                        "Waste clearly contained inside the skip is excluded from this accumulation rule.",
                    ],
                    evidence_classes=["waste_skip", "trash/bag"],
                    track_ids=track_ids,
                    waste_track_ids=sorted(state["waste_ids"]),
                    incident_type="skip_overflow",
                    details={
                        "association_hits": state["concerning_hits"],
                        "relations": sorted(state["relations"]),
                    },
                )
                self._upsert_occurrence(occurrence)
                self._store_rule(RuleAssessment(
                    rule=f"skip_monitoring:{skip_id}",
                    title="Persistent waste accumulation around skip",
                    status="candidate",
                    confidence=occurrence.confidence,
                    reasons=occurrence.reasons,
                    evidence_classes=["waste_skip", "trash/bag"],
                    incident_type="skip_overflow",
                    related_track_ids=track_ids,
                ))

        # --------------------------------------------------------
        # Road damage persistence and pothole <-> crack grouping.
        # --------------------------------------------------------
        for detection in observed_detections:
            if detection["class_name"] not in {"pothole", "road_crack"}:
                continue
            track_id = self._track_id(detection)
            if not track_id:
                continue
            self.road_track_hits[track_id] += 1
            self.road_track_confidence[track_id] = max(
                self.road_track_confidence.get(track_id, 0.0),
                float(detection["confidence"]),
            )
            if self.road_track_hits[track_id] >= 3:
                incident_type = "pothole" if detection["class_name"] == "pothole" else "road_damage"
                occurrence = Occurrence(
                    occurrence_id=f"ROAD-DAMAGE-{track_id}",
                    occurrence_type="road_damage",
                    title="Persistent road damage",
                    status="candidate",
                    confidence=self.road_track_confidence[track_id],
                    reasons=[f"The same {detection['class_name']} track persisted across multiple sampled frames."],
                    evidence_classes=[detection["class_name"]],
                    track_ids=[track_id],
                    incident_type=incident_type,
                    follow_up="Use camera/GIS position to deduplicate repeat observations of the same road defect over time.",
                    details={"persistence_hits": self.road_track_hits[track_id]},
                )
                self._upsert_occurrence(occurrence)

        for link in _associations_of(associations, "road_damage"):
            pothole_id = link.get("left_track_id")
            crack_id = link.get("right_track_id")
            if not pothole_id or not crack_id:
                continue
            pair = (str(pothole_id), str(crack_id))
            self.road_pair_hits[pair] += 1
            if self.road_pair_hits[pair] >= 2:
                confidence = float(link["confidence"])
                occurrence = Occurrence(
                    occurrence_id=f"ROAD-GROUP-{pair[0]}-{pair[1]}",
                    occurrence_type="road_damage",
                    title="Grouped pothole and road-crack damage",
                    status="candidate",
                    confidence=confidence,
                    reasons=["A pothole and road crack remain spatially associated in the same road area."],
                    evidence_classes=["pothole", "road_crack"],
                    track_ids=[pair[0], pair[1]],
                    incident_type="road_damage",
                    follow_up="Use GIS to keep this as one road-damage occurrence rather than duplicate incidents.",
                    details={"grouping_hits": self.road_pair_hits[pair]},
                )
                self._upsert_occurrence(occurrence)
                self._store_rule(RuleAssessment(
                    rule=f"road_damage_group:{pair[0]}:{pair[1]}",
                    title="Pothole and crack grouped as road damage",
                    status="candidate",
                    confidence=confidence,
                    reasons=occurrence.reasons,
                    evidence_classes=["pothole", "road_crack"],
                    incident_type="road_damage",
                    related_track_ids=[pair[0], pair[1]],
                ))

        return detections

    def _cleaner_performance(self) -> dict[str, Any] | None:
        cleaning_occurrences = [
            item for item in self.occurrences.values()
            if item.occurrence_type == "cleaning_activity"
        ]
        cleanliness = summarize_cleanliness_history(self.cleanliness_history)
        if not cleaning_occurrences or not cleanliness:
            return None

        before = float(cleanliness.get("before_score", cleanliness["score"]))
        after = float(cleanliness.get("after_score", cleanliness["score"]))
        change = round(after - before, 1)

        if change >= 15:
            status = "effective"
            title = "Cleaning activity improved street cleanliness"
            reason = "The provisional street-cleanliness score improved materially from the beginning to the end of the sampled video."
        elif change >= 5:
            status = "improved"
            title = "Cleaning activity produced some improvement"
            reason = "The street-cleanliness score improved, but the change is below the initial strong-improvement threshold."
        elif change > -5:
            status = "review"
            title = "Cleaning activity observed with limited cleanliness change"
            reason = "Cleaner presence/activity was observed, but the visible street condition changed very little."
        else:
            status = "review"
            title = "Cleaning activity observed while visible cleanliness worsened"
            reason = "The visible cleanliness score decreased; review the scene and rule assumptions before drawing a performance conclusion."

        related = sorted({
            track_id
            for item in cleaning_occurrences
            for track_id in item.track_ids
        })
        confidence = max(item.confidence for item in cleaning_occurrences)
        return {
            "status": status,
            "title": title,
            "confidence": round(confidence, 4),
            "before_score": before,
            "after_score": after,
            "change": change,
            "reasons": [
                reason,
                "This Test Lab assessment does not yet include the cleaner's assigned GIS zone or scheduled shift.",
            ],
            "related_track_ids": related,
        }

    def results(self) -> dict[str, Any]:
        cleanliness = summarize_cleanliness_history(self.cleanliness_history)

        # Do not call a street-cleanliness condition "persistent" because of
        # one or two false-positive waste detections in an unrelated video.
        # A concerning state must occupy a meaningful portion of the recent
        # sampled-frame window before the rule is surfaced.
        recent_window = int(cleanliness.get("recent_window", 0)) if cleanliness else 0
        recent_concerning = int(cleanliness.get("recent_concerning_frames", 0)) if cleanliness else 0
        recent_ratio = float(cleanliness.get("recent_concerning_ratio", 0.0)) if cleanliness else 0.0
        cleanliness_persistent = (
            bool(cleanliness)
            and cleanliness["state"] in {"littered", "poor"}
            and recent_window >= 3
            and recent_concerning >= 3
            and recent_ratio >= 0.35
        )

        if cleanliness_persistent:
            self._store_rule(RuleAssessment(
                rule="street_cleanliness",
                title="Persistent street cleanliness condition",
                status="observation",
                confidence=min(1.0, max(0.5, (100.0 - float(cleanliness["score"])) / 100.0 + 0.35)),
                reasons=list(cleanliness["reasons"]) + [
                    f"Concerning cleanliness was present in {recent_concerning}/{recent_window} recent sampled frames."
                ],
                evidence_classes=["trash", "bag", "waste_skip"],
                details={
                    "score": cleanliness["score"],
                    "before_score": cleanliness.get("before_score"),
                    "after_score": cleanliness.get("after_score"),
                    "change": cleanliness.get("change"),
                    "recent_concerning_frames": recent_concerning,
                    "recent_window": recent_window,
                    "recent_concerning_ratio": recent_ratio,
                },
            ))

        # If a pothole/crack pair was grouped, suppress duplicate single-track
        # road occurrences for those same tracks in the final Test Lab output.
        grouped_tracks = {
            track_id
            for occurrence in self.occurrences.values()
            if occurrence.occurrence_id.startswith("ROAD-GROUP-")
            for track_id in occurrence.track_ids
        }
        occurrences = [
            item
            for item in self.occurrences.values()
            if not (
                item.occurrence_id.startswith("ROAD-DAMAGE-")
                and any(track_id in grouped_tracks for track_id in item.track_ids)
            )
        ]

        return {
            "rules": [item.as_dict() for item in self.rules.values()],
            "occurrences": [item.as_dict() for item in occurrences],
            "street_cleanliness": cleanliness,
            "cleaner_performance": self._cleaner_performance(),
            "tracks": self.tracker.summaries(),
            "association_summary": [
                {"association_type": name, "hits": hits}
                for name, hits in sorted(self.association_counts.items())
            ],
        }
