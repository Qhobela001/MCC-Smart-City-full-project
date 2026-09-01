from __future__ import annotations

from statistics import mean
from typing import Any

from .associations import bbox_area, build_associations


def _state_for_score(score: float) -> str:
    if score >= 90:
        return "clean"
    if score >= 75:
        return "acceptable"
    if score >= 50:
        return "littered"
    return "poor"


def assess_street_cleanliness(
    detections: list[dict[str, Any]],
    image_width: int,
    image_height: int,
    associations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Estimate a provisional cleanliness state for the visible camera zone.

    This is intentionally an interpretable heuristic for Test Lab validation,
    not a final municipal cleanliness standard. Waste inside a detected skip is
    treated differently from loose/persistent waste around the street.
    """

    associations = associations if associations is not None else build_associations(detections)

    waste_indices = {
        index
        for index, detection in enumerate(detections)
        if detection["class_name"] in {"trash", "bag"}
    }
    contained: set[int] = set()
    around_skip: set[int] = set()
    above_skip: set[int] = set()

    for association in associations:
        if association["association_type"] != "waste_skip":
            continue
        waste_index = int(association["right_index"])
        relation = association["relation"]
        if relation == "inside_skip":
            contained.add(waste_index)
        elif relation == "above_skip":
            above_skip.add(waste_index)
        elif relation == "around_skip":
            around_skip.add(waste_index)

    loose = waste_indices - contained - around_skip - above_skip

    frame_area = max(float(image_width * image_height), 1.0)
    loose_area_ratio = sum(bbox_area(detections[i]) for i in loose) / frame_area
    around_area_ratio = sum(bbox_area(detections[i]) for i in around_skip | above_skip) / frame_area

    # Interpretable first-pass scoring. This can later be calibrated against
    # MCC field ratings while preserving the same response contract.
    penalty = 0.0
    penalty += min(45.0, len(loose) * 9.0)
    penalty += min(30.0, len(around_skip) * 8.0)
    penalty += min(35.0, len(above_skip) * 11.0)
    penalty += min(20.0, loose_area_ratio * 900.0)
    penalty += min(15.0, around_area_ratio * 650.0)

    score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)
    state = _state_for_score(score)

    reasons: list[str] = []
    if not waste_indices:
        reasons.append("No trash or loose bags were detected in the visible zone.")
    if loose:
        reasons.append(f"{len(loose)} loose waste object(s) were detected away from a waste skip.")
    if around_skip:
        reasons.append(f"{len(around_skip)} waste object(s) were detected around a waste skip.")
    if above_skip:
        reasons.append(f"{len(above_skip)} waste object(s) appear above/around the upper skip boundary.")
    if contained:
        reasons.append(f"{len(contained)} waste object(s) appear contained inside a detected waste skip and are not penalized as street litter.")

    return {
        "score": score,
        "state": state,
        "loose_waste_count": len(loose),
        "contained_waste_count": len(contained),
        "waste_around_skip_count": len(around_skip),
        "waste_above_skip_count": len(above_skip),
        "total_waste_count": len(waste_indices),
        "provisional": True,
        "reasons": reasons,
    }


def summarize_cleanliness_history(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Summarise video cleanliness using recent-frame persistence, not one frame.

    A single false-positive trash detection should not make an unrelated video
    look like a persistent street-cleanliness problem. The final state therefore
    uses an average of a recent window and reports how often concerning states
    actually occurred. Before/after windows are still preserved for cleaner
    performance evaluation.
    """
    if not history:
        return None

    window = max(3, min(12, len(history) // 6 or 3))
    before_window = history[:window]
    after_window = history[-window:]

    before = round(mean(float(item["score"]) for item in before_window), 1)
    after = round(mean(float(item["score"]) for item in after_window), 1)
    change = round(after - before, 1)

    def average_count(key: str) -> int:
        return int(round(mean(float(item[key]) for item in after_window)))

    recent_concerning = sum(
        1 for item in after_window if item["state"] in {"littered", "poor"}
    )
    total_concerning = sum(
        1 for item in history if item["state"] in {"littered", "poor"}
    )

    loose = average_count("loose_waste_count")
    contained = average_count("contained_waste_count")
    around = average_count("waste_around_skip_count")
    above = average_count("waste_above_skip_count")
    total = average_count("total_waste_count")

    state = _state_for_score(after)
    reasons: list[str] = []
    if total == 0:
        reasons.append("No persistent trash or loose bags were detected across the recent sampled frames.")
    if loose:
        reasons.append(f"Approximately {loose} loose waste object(s) persisted across the recent sampled frames.")
    if around:
        reasons.append(f"Approximately {around} waste object(s) persisted around a detected waste skip.")
    if above:
        reasons.append(f"Approximately {above} waste object(s) persisted above/around the upper skip boundary.")
    if contained:
        reasons.append(f"Approximately {contained} waste object(s) appeared contained inside a waste skip and were not penalized as street litter.")

    return {
        "score": after,
        "state": state,
        "loose_waste_count": loose,
        "contained_waste_count": contained,
        "waste_around_skip_count": around,
        "waste_above_skip_count": above,
        "total_waste_count": total,
        "provisional": True,
        "reasons": reasons,
        "before_score": before,
        "after_score": after,
        "change": change,
        "sampled_assessments": len(history),
        "recent_window": len(after_window),
        "recent_concerning_frames": recent_concerning,
        "recent_concerning_ratio": round(recent_concerning / max(len(after_window), 1), 4),
        "total_concerning_frames": total_concerning,
        "total_concerning_ratio": round(total_concerning / max(len(history), 1), 4),
    }
