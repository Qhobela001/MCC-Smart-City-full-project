from __future__ import annotations

from math import hypot
from typing import Any


BBoxDict = dict[str, float]
DetectionDict = dict[str, Any]


def bbox_center(detection: DetectionDict) -> tuple[float, float]:
    box = detection["bbox"]
    return (
        (float(box["x1"]) + float(box["x2"])) / 2.0,
        (float(box["y1"]) + float(box["y2"])) / 2.0,
    )


def bbox_diagonal(detection: DetectionDict) -> float:
    box = detection["bbox"]
    return hypot(float(box["width"]), float(box["height"]))


def bbox_area(detection: DetectionDict) -> float:
    box = detection["bbox"]
    return max(0.0, float(box["width"])) * max(0.0, float(box["height"]))


def bbox_iou(a: DetectionDict, b: DetectionDict) -> float:
    ab = a["bbox"]
    bb = b["bbox"]

    x1 = max(float(ab["x1"]), float(bb["x1"]))
    y1 = max(float(ab["y1"]), float(bb["y1"]))
    x2 = min(float(ab["x2"]), float(bb["x2"]))
    y2 = min(float(ab["y2"]), float(bb["y2"]))

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection <= 0.0:
        return 0.0

    union = bbox_area(a) + bbox_area(b) - intersection
    if union <= 0.0:
        return 0.0

    return intersection / union


def normalized_center_distance(a: DetectionDict, b: DetectionDict) -> float:
    ax, ay = bbox_center(a)
    bx, by = bbox_center(b)
    distance = hypot(ax - bx, ay - by)
    scale = max(bbox_diagonal(a), bbox_diagonal(b), 1.0)
    return distance / scale


def is_near(a: DetectionDict, b: DetectionDict, multiplier: float = 1.6) -> bool:
    return normalized_center_distance(a, b) <= multiplier


def center_inside(inner: DetectionDict, outer: DetectionDict, margin: float = 0.0) -> bool:
    cx, cy = bbox_center(inner)
    box = outer["bbox"]
    width = max(float(box["width"]), 1.0)
    height = max(float(box["height"]), 1.0)
    return (
        float(box["x1"]) - width * margin <= cx <= float(box["x2"]) + width * margin
        and float(box["y1"]) - height * margin <= cy <= float(box["y2"]) + height * margin
    )


def _confidence(a: DetectionDict, b: DetectionDict) -> float:
    return round(min(float(a["confidence"]), float(b["confidence"])), 4)


def _association(
    association_type: str,
    left_index: int,
    left: DetectionDict,
    right_index: int,
    right: DetectionDict,
    relation: str,
    *,
    confidence: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "association_type": association_type,
        "left_index": left_index,
        "left_class": left["class_name"],
        "left_track_id": left.get("track_id"),
        "right_index": right_index,
        "right_class": right["class_name"],
        "right_track_id": right.get("track_id"),
        "relation": relation,
        "confidence": round(
            confidence if confidence is not None else _confidence(left, right), 4
        ),
        "metadata": metadata or {},
    }


def build_associations(detections: list[DetectionDict]) -> list[dict[str, Any]]:
    """Build reusable spatial relationships between raw MCC detections.

    A detection remains a raw visual fact. These relationships are the first
    contextual layer used later by temporal rules and occurrences.
    """

    by_class: dict[str, list[tuple[int, DetectionDict]]] = {}
    for index, detection in enumerate(detections):
        by_class.setdefault(str(detection["class_name"]), []).append((index, detection))

    cars = by_class.get("car", [])
    plates = by_class.get("license_plate", [])
    smoke = by_class.get("vehicle_smoke", [])
    persons = by_class.get("person", [])
    trash = by_class.get("trash", []) + by_class.get("bag", [])
    # A transient weak waste_skip detection can be explicitly marked by the
    # video rule engine as unclassified waste/debris. Keep the raw YOLO class
    # unchanged, but include that detection in dumping associations only.
    transient_skip_waste = [
        (index, detection)
        for index, detection in by_class.get("waste_skip", [])
        if detection.get("dumping_role") == "unclassified_waste_candidate"
    ]
    trash = trash + transient_skip_waste
    brooms = by_class.get("broom", [])
    skips = [
        (index, detection)
        for index, detection in by_class.get("waste_skip", [])
        if detection.get("dumping_role") != "unclassified_waste_candidate"
    ]
    potholes = by_class.get("pothole", [])
    cracks = by_class.get("road_crack", [])

    associations: list[dict[str, Any]] = []

    # ------------------------------------------------------------
    # Vehicle <-> plate
    # Assign each plate to the single best vehicle.
    # ------------------------------------------------------------
    for plate_index, plate in plates:
        parent_index = plate.get("parent_detection_index")
        if isinstance(parent_index, int) and 0 <= parent_index < len(detections):
            parent = detections[parent_index]
            if parent.get("class_name") == "car":
                associations.append(
                    _association(
                        "car_plate",
                        parent_index,
                        parent,
                        plate_index,
                        plate,
                        "vehicle_detail_crop",
                        metadata={"plate_status": "detected", "source": plate.get("source", "vehicle_detail")},
                    )
                )
                continue

        candidates: list[tuple[float, int, DetectionDict, str]] = []
        for car_index, car in cars:
            inside = center_inside(plate, car, margin=0.08)
            distance = normalized_center_distance(plate, car)
            if inside or distance <= 1.05:
                score = (2.0 if inside else 0.0) + max(0.0, 1.2 - distance)
                candidates.append((score, car_index, car, "inside_vehicle" if inside else "near_vehicle"))
        if candidates:
            _, car_index, car, relation = max(candidates, key=lambda item: item[0])
            associations.append(
                _association(
                    "car_plate",
                    car_index,
                    car,
                    plate_index,
                    plate,
                    relation,
                    metadata={"plate_status": "detected"},
                )
            )

    # ------------------------------------------------------------
    # Vehicle <-> smoke
    # Secondary vehicle-crop detections contain parent_detection_index,
    # which is stronger than geometry alone.
    # ------------------------------------------------------------
    for smoke_index, plume in smoke:
        parent_index = plume.get("parent_detection_index")
        if isinstance(parent_index, int) and 0 <= parent_index < len(detections):
            parent = detections[parent_index]
            if parent.get("class_name") == "car":
                associations.append(
                    _association(
                        "car_smoke",
                        parent_index,
                        parent,
                        smoke_index,
                        plume,
                        "vehicle_detail_crop",
                        metadata={"source": plume.get("source", "vehicle_detail")},
                    )
                )
                continue

        candidates = []
        for car_index, car in cars:
            distance = normalized_center_distance(plume, car)
            if distance <= 1.9:
                candidates.append((distance, car_index, car))
        if candidates:
            distance, car_index, car = min(candidates, key=lambda item: item[0])
            associations.append(
                _association(
                    "car_smoke",
                    car_index,
                    car,
                    smoke_index,
                    plume,
                    "near_vehicle",
                    metadata={"normalized_distance": round(distance, 3)},
                )
            )

    # ------------------------------------------------------------
    # Vehicle <-> waste
    # Supports dumping-from-vehicle sequences where a person is partly or
    # completely occluded but a waste object is observed at the vehicle.
    # ------------------------------------------------------------
    for car_index, car in cars:
        for waste_index, waste_item in trash:
            distance = normalized_center_distance(car, waste_item)
            max_distance = 1.55 if waste_item.get("dumping_role") == "unclassified_waste_candidate" else 1.20
            if distance <= max_distance:
                associations.append(
                    _association(
                        "car_waste",
                        car_index,
                        car,
                        waste_index,
                        waste_item,
                        "near_vehicle",
                        metadata={"normalized_distance": round(distance, 3)},
                    )
                )

    # ------------------------------------------------------------
    # Person <-> waste and person <-> car
    # ------------------------------------------------------------
    for person_index, person in persons:
        for waste_index, waste_item in trash:
            distance = normalized_center_distance(person, waste_item)
            max_distance = 1.85 if waste_item.get("dumping_role") == "unclassified_waste_candidate" else 1.55
            if distance <= max_distance:
                associations.append(
                    _association(
                        "person_waste",
                        person_index,
                        person,
                        waste_index,
                        waste_item,
                        "near",
                        metadata={"normalized_distance": round(distance, 3)},
                    )
                )

        for car_index, car in cars:
            if is_near(person, car, 1.25):
                associations.append(
                    _association(
                        "person_car",
                        person_index,
                        person,
                        car_index,
                        car,
                        "near_vehicle",
                    )
                )

        for broom_index, broom in brooms:
            if is_near(person, broom, 1.4):
                associations.append(
                    _association(
                        "person_broom",
                        person_index,
                        person,
                        broom_index,
                        broom,
                        "near",
                    )
                )

    # ------------------------------------------------------------
    # Waste <-> skip
    # This relationship is deliberately richer than "near" because waste
    # inside a skip should not be treated like waste left beside the skip.
    # ------------------------------------------------------------
    for skip_index, skip in skips:
        skip_box = skip["bbox"]
        skip_height = max(float(skip_box["height"]), 1.0)
        for waste_index, waste_item in trash:
            if center_inside(waste_item, skip, margin=0.02):
                relation = "inside_skip"
            elif is_near(skip, waste_item, 1.1):
                _, waste_cy = bbox_center(waste_item)
                relation = (
                    "above_skip"
                    if waste_cy < float(skip_box["y1"]) + 0.20 * skip_height
                    else "around_skip"
                )
            else:
                continue

            associations.append(
                _association(
                    "waste_skip",
                    skip_index,
                    skip,
                    waste_index,
                    waste_item,
                    relation,
                )
            )

    # ------------------------------------------------------------
    # Road-damage grouping
    # ------------------------------------------------------------
    for pothole_index, pothole in potholes:
        for crack_index, crack in cracks:
            if is_near(pothole, crack, 1.7):
                associations.append(
                    _association(
                        "road_damage",
                        pothole_index,
                        pothole,
                        crack_index,
                        crack,
                        "same_road_area",
                    )
                )

    return associations
