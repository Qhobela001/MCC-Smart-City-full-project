from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class QualificationRule:
    event_type: str
    min_confidence: float
    min_hits: int
    context_class: str | None = None


DEFAULT_RULES = {
    "trash": QualificationRule("illegal_dumping", 0.45, 3, "person"),
    "bag": QualificationRule("illegal_dumping", 0.45, 3, "person"),
    "vehicle_smoke": QualificationRule("vehicle_smoke_emission", 0.50, 3, "car"),
    "waste_skip": QualificationRule("skip_overflow", 0.55, 3),
    "pothole": QualificationRule("pothole", 0.55, 3),
    "road_crack": QualificationRule("road_damage", 0.55, 3),
}


@dataclass
class Track:
    track_id: int
    class_name: str
    first_seen: datetime
    last_seen: datetime
    last_bbox: dict
    hits: int = 1
    confidence_sum: float = 0.0
    max_confidence: float = 0.0
    emitted: bool = False
    last_frame_sequence: int = -1


def _centre(bbox: dict) -> tuple[float, float]:
    return (
        (float(bbox["x1"]) + float(bbox["x2"])) / 2,
        (float(bbox["y1"]) + float(bbox["y2"])) / 2,
    )


def _diagonal(bbox: dict) -> float:
    return max(
        1.0,
        math.hypot(
            float(bbox["x2"]) - float(bbox["x1"]),
            float(bbox["y2"]) - float(bbox["y1"]),
        ),
    )


def _near(left: dict, right: dict, factor: float = 4.0) -> bool:
    lx, ly = _centre(left)
    rx, ry = _centre(right)
    return math.hypot(lx - rx, ly - ry) <= factor * max(
        _diagonal(left), _diagonal(right)
    )


@dataclass
class EventQualifier:
    audit_path: Path
    max_gap_seconds: float = 8.0
    context_window_seconds: float = 10.0
    cooldown_seconds: float = 60.0
    rules: dict[str, QualificationRule] = field(
        default_factory=lambda: dict(DEFAULT_RULES)
    )
    tracks: list[Track] = field(default_factory=list)
    recent_context: dict[str, list[tuple[datetime, dict]]] = field(default_factory=dict)
    cooldowns: dict[str, datetime] = field(default_factory=dict)
    next_track_id: int = 1

    def _audit(self, record: dict) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _purge(self, now: datetime) -> None:
        self.tracks = [
            item for item in self.tracks
            if (now - item.last_seen).total_seconds() <= self.max_gap_seconds
        ]
        for class_name, items in list(self.recent_context.items()):
            current = [
                item for item in items
                if (now - item[0]).total_seconds() <= self.context_window_seconds
            ]
            if current:
                self.recent_context[class_name] = current
            else:
                self.recent_context.pop(class_name, None)

    def observe(
        self, detections: list[dict], captured_at: datetime, frame_sequence: int
    ) -> tuple[list[dict], list[dict]]:
        self._purge(captured_at)
        for detection in detections:
            if detection["class_name"] in {"person", "car"}:
                self.recent_context.setdefault(detection["class_name"], []).append(
                    (captured_at, detection["bbox"])
                )

        qualified: list[dict] = []
        decisions: list[dict] = []
        for detection in detections:
            class_name = detection["class_name"]
            rule = self.rules.get(class_name)
            if rule is None:
                reason = (
                    "context_only"
                    if class_name in {"person", "car"}
                    else "non_candidate_class"
                )
                decision = {
                    "captured_at": captured_at.isoformat(),
                    "frame_sequence": frame_sequence,
                    "class_name": class_name,
                    "confidence": round(float(detection["confidence"]), 6),
                    "event_type": None,
                    "track_id": None,
                    "hits": 0,
                    "required_hits": 0,
                    "required_context": None,
                    "context_found": False,
                    "decision": "ignored",
                    "reason": reason,
                    "stage": "AI-3",
                    "is_test": True,
                }
                self._audit(decision)
                decisions.append(decision)
                continue
            confidence = float(detection["confidence"])
            if confidence < rule.min_confidence:
                decision = self._decision(
                    captured_at, frame_sequence, detection, None, "rejected",
                    "below_confidence", rule,
                )
                self._audit(decision)
                decisions.append(decision)
                continue

            candidates = [
                item for item in self.tracks
                if item.class_name == class_name
                and item.last_frame_sequence != frame_sequence
                and _near(item.last_bbox, detection["bbox"], 1.5)
            ]
            if candidates:
                track = min(
                    candidates,
                    key=lambda item: math.hypot(
                        _centre(item.last_bbox)[0] - _centre(detection["bbox"])[0],
                        _centre(item.last_bbox)[1] - _centre(detection["bbox"])[1],
                    ),
                )
                track.hits += 1
                track.last_seen = captured_at
                track.last_bbox = detection["bbox"]
                track.confidence_sum += confidence
                track.max_confidence = max(track.max_confidence, confidence)
                track.last_frame_sequence = frame_sequence
            else:
                track = Track(
                    track_id=self.next_track_id,
                    class_name=class_name,
                    first_seen=captured_at,
                    last_seen=captured_at,
                    last_bbox=detection["bbox"],
                    confidence_sum=confidence,
                    max_confidence=confidence,
                    last_frame_sequence=frame_sequence,
                )
                self.next_track_id += 1
                self.tracks.append(track)

            reason = "insufficient_persistence"
            status = "rejected"
            context_found = rule.context_class is None
            if rule.context_class:
                context_found = any(
                    _near(detection["bbox"], bbox)
                    for _, bbox in self.recent_context.get(rule.context_class, [])
                )
            if track.hits >= rule.min_hits and not context_found:
                reason = f"missing_{rule.context_class}_context"
            elif track.hits >= rule.min_hits:
                centre_x, centre_y = _centre(detection["bbox"])
                cooldown_key = (
                    f"{rule.event_type}:{class_name}:"
                    f"{int(centre_x // 200)}:{int(centre_y // 200)}"
                )
                previous = self.cooldowns.get(cooldown_key)
                if track.emitted:
                    reason = "track_already_emitted"
                elif previous and (captured_at - previous).total_seconds() < self.cooldown_seconds:
                    reason = "event_cooldown"
                else:
                    status = "qualified"
                    reason = "rule_satisfied"
                    track.emitted = True
                    self.cooldowns[cooldown_key] = captured_at
                    enriched = dict(detection)
                    enriched["qualification"] = {
                        "event_type": rule.event_type,
                        "track_id": track.track_id,
                        "hits": track.hits,
                        "duration_seconds": round(
                            (track.last_seen - track.first_seen).total_seconds(), 3
                        ),
                        "average_confidence": round(track.confidence_sum / track.hits, 6),
                        "max_confidence": round(track.max_confidence, 6),
                        "required_context": rule.context_class,
                        "context_found": context_found,
                        "decision": status,
                        "reason": reason,
                    }
                    qualified.append(enriched)

            decision = self._decision(
                captured_at, frame_sequence, detection, track, status, reason, rule,
                context_found,
            )
            self._audit(decision)
            decisions.append(decision)
        return qualified, decisions

    @staticmethod
    def _decision(
        captured_at: datetime,
        frame_sequence: int,
        detection: dict,
        track: Track | None,
        status: str,
        reason: str,
        rule: QualificationRule,
        context_found: bool = False,
    ) -> dict:
        return {
            "captured_at": captured_at.isoformat(),
            "frame_sequence": frame_sequence,
            "class_name": detection["class_name"],
            "confidence": round(float(detection["confidence"]), 6),
            "event_type": rule.event_type,
            "track_id": track.track_id if track else None,
            "hits": track.hits if track else 0,
            "required_hits": rule.min_hits,
            "required_context": rule.context_class,
            "context_found": context_found,
            "decision": status,
            "reason": reason,
            "stage": "AI-3",
            "is_test": True,
        }
