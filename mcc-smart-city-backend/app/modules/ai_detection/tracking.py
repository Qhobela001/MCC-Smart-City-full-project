from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .associations import bbox_iou, normalized_center_distance


PREFIXES = {
    "person": "PERSON",
    "trash": "TRASH",
    "bag": "BAG",
    "car": "CAR",
    "license_plate": "PLATE",
    "vehicle_smoke": "SMOKE",
    "pothole": "POTHOLE",
    "road_crack": "CRACK",
    "broom": "BROOM",
    "waste_skip": "SKIP",
}

# Display persistence is deliberately class-aware. Dynamic objects are held for
# a short gap, while static scene features can remain longer. These are UI /
# tracking continuity windows only; predicted boxes never count as new AI
# evidence for the rule engine.
DEFAULT_HOLD_SECONDS = {
    "person": 1.20,
    "car": 1.50,
    "license_plate": 1.00,
    "vehicle_smoke": 1.25,
    "trash": 2.00,
    "bag": 2.00,
    "broom": 1.20,
    "waste_skip": 4.00,
    "pothole": 4.00,
    "road_crack": 4.00,
}


@dataclass
class Track:
    track_id: str
    class_name: str
    class_id: int | None
    bbox: dict[str, float]
    first_frame: int
    last_frame: int
    hits: int = 1
    misses: int = 0
    max_confidence: float = 0.0
    last_confidence: float = 0.0
    source: str = "primary"
    first_seen_seconds: float = 0.0
    last_seen_seconds: float = 0.0
    last_update_seconds: float = 0.0
    previous_observed_bbox: dict[str, float] | None = None
    previous_seen_seconds: float | None = None
    velocity: dict[str, float] = field(
        default_factory=lambda: {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}
    )
    predicted_frames: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "first_sampled_frame": self.first_frame,
            "last_sampled_frame": self.last_frame,
            "hits": self.hits,
            "predicted_frames": self.predicted_frames,
            "max_confidence": round(self.max_confidence, 4),
            "first_seen_seconds": round(self.first_seen_seconds, 3),
            "last_seen_seconds": round(self.last_seen_seconds, 3),
        }


class SimpleObjectTracker:
    """Class-aware Test Lab tracker with short-gap prediction.

    The tracker preserves a stable rectangle/track ID when YOLO temporarily
    misses an already observed object. Predicted rectangles are explicitly
    labelled ``is_predicted=True`` so they can be drawn by the UI without being
    counted as fresh model evidence.

    Production live streams can later replace this lightweight tracker with
    ByteTrack/BoT-SORT while keeping the same track_id / tracking_state
    contract used by the rule engine and frontend.
    """

    def __init__(
        self,
        max_misses: int = 60,
        *,
        hold_seconds: dict[str, float] | None = None,
    ) -> None:
        self.max_misses = max_misses
        self.hold_seconds = {**DEFAULT_HOLD_SECONDS, **(hold_seconds or {})}
        self._tracks: dict[str, Track] = {}
        self._history: dict[str, Track] = {}
        self._counters: dict[str, int] = {}

    def _new_id(self, class_name: str) -> str:
        number = self._counters.get(class_name, 0) + 1
        self._counters[class_name] = number
        prefix = PREFIXES.get(class_name, class_name.upper())
        return f"{prefix}-{number:04d}"

    @staticmethod
    def _copy_bbox(bbox: dict[str, Any]) -> dict[str, float]:
        return {
            "x1": float(bbox["x1"]),
            "y1": float(bbox["y1"]),
            "x2": float(bbox["x2"]),
            "y2": float(bbox["y2"]),
            "width": float(bbox["width"]),
            "height": float(bbox["height"]),
        }

    @staticmethod
    def _bbox_from_corners(x1: float, y1: float, x2: float, y2: float) -> dict[str, float]:
        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width": max(1.0, x2 - x1),
            "height": max(1.0, y2 - y1),
        }

    @staticmethod
    def _clamp_bbox(
        bbox: dict[str, float], image_width: int | None, image_height: int | None
    ) -> dict[str, float]:
        x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
        if image_width and image_width > 1:
            x1 = max(0.0, min(x1, float(image_width - 1)))
            x2 = max(x1 + 1.0, min(x2, float(image_width)))
        if image_height and image_height > 1:
            y1 = max(0.0, min(y1, float(image_height - 1)))
            y2 = max(y1 + 1.0, min(y2, float(image_height)))
        return SimpleObjectTracker._bbox_from_corners(x1, y1, x2, y2)

    def _hold_seconds(self, class_name: str) -> float:
        return max(0.1, float(self.hold_seconds.get(class_name, 1.0)))

    def _predict_bbox(
        self,
        track: Track,
        current_time: float,
        image_width: int | None,
        image_height: int | None,
    ) -> dict[str, float]:
        age = max(0.0, current_time - track.last_seen_seconds)
        # Avoid wild extrapolation when a detection has been missing too long.
        dt = min(age, self._hold_seconds(track.class_name))
        base = track.bbox
        predicted = self._bbox_from_corners(
            base["x1"] + track.velocity["x1"] * dt,
            base["y1"] + track.velocity["y1"] * dt,
            base["x2"] + track.velocity["x2"] * dt,
            base["y2"] + track.velocity["y2"] * dt,
        )
        return self._clamp_bbox(predicted, image_width, image_height)

    def _update_velocity(self, track: Track, new_bbox: dict[str, float], current_time: float) -> None:
        dt = current_time - track.last_seen_seconds
        if dt <= 1e-6:
            return

        old = track.bbox
        measured = {
            "x1": (new_bbox["x1"] - old["x1"]) / dt,
            "y1": (new_bbox["y1"] - old["y1"]) / dt,
            "x2": (new_bbox["x2"] - old["x2"]) / dt,
            "y2": (new_bbox["y2"] - old["y2"]) / dt,
        }

        # A smoothed velocity makes the short prediction window less jittery.
        alpha = 0.45 if track.hits > 1 else 1.0
        for key in track.velocity:
            track.velocity[key] = (1.0 - alpha) * track.velocity[key] + alpha * measured[key]

    def update(
        self,
        detections: list[dict[str, Any]],
        frame_index: int,
        *,
        time_seconds: float | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> list[dict[str, Any]]:
        current_time = float(time_seconds) if time_seconds is not None else float(frame_index)
        active_tracks = list(self._tracks.values())
        used_track_ids: set[str] = set()
        matched: dict[int, str] = {}

        # Highest-confidence detections are matched first.
        ordered = sorted(
            enumerate(detections),
            key=lambda item: float(item[1].get("confidence", 0.0)),
            reverse=True,
        )

        for original_index, detection in ordered:
            class_name = str(detection["class_name"])
            candidates: list[tuple[float, Track]] = []

            for track in active_tracks:
                if track.track_id in used_track_ids or track.class_name != class_name:
                    continue

                predicted_bbox = self._predict_bbox(track, current_time, image_width, image_height)
                synthetic = {"bbox": predicted_bbox}
                iou = bbox_iou(detection, synthetic)
                distance = normalized_center_distance(detection, synthetic)

                # IoU is preferred. Centre distance handles larger jumps between
                # sampled video frames and temporary detector misses.
                if iou >= 0.05 or distance <= 1.35:
                    score = iou * 2.2 + max(0.0, 1.40 - distance)
                    candidates.append((score, track))

            new_bbox = self._copy_bbox(detection["bbox"])
            if candidates:
                _, track = max(candidates, key=lambda item: item[0])
                used_track_ids.add(track.track_id)
                matched[original_index] = track.track_id

                track.previous_observed_bbox = dict(track.bbox)
                track.previous_seen_seconds = track.last_seen_seconds
                self._update_velocity(track, new_bbox, current_time)
                track.bbox = new_bbox
                track.last_frame = frame_index
                track.hits += 1
                track.misses = 0
                track.max_confidence = max(track.max_confidence, float(detection["confidence"]))
                track.last_confidence = float(detection["confidence"])
                track.source = str(detection.get("source", track.source))
                track.last_seen_seconds = current_time
                track.last_update_seconds = current_time
            else:
                track_id = self._new_id(class_name)
                track = Track(
                    track_id=track_id,
                    class_name=class_name,
                    class_id=int(detection["class_id"]) if detection.get("class_id") is not None else None,
                    bbox=new_bbox,
                    first_frame=frame_index,
                    last_frame=frame_index,
                    max_confidence=float(detection["confidence"]),
                    last_confidence=float(detection["confidence"]),
                    source=str(detection.get("source", "primary")),
                    first_seen_seconds=current_time,
                    last_seen_seconds=current_time,
                    last_update_seconds=current_time,
                )
                self._tracks[track_id] = track
                active_tracks.append(track)
                used_track_ids.add(track_id)
                matched[original_index] = track_id

        # Update missed tracks and retire tracks only after the generous internal
        # miss budget. The visible prediction window below is much shorter.
        for track in list(self._tracks.values()):
            if track.track_id not in used_track_ids:
                track.misses += 1
                track.last_update_seconds = current_time
                if track.misses > self.max_misses:
                    self._history[track.track_id] = track
                    del self._tracks[track.track_id]

        output: list[dict[str, Any]] = []

        # Fresh model detections always take precedence.
        for index, detection in enumerate(detections):
            enriched = dict(detection)
            enriched["track_id"] = matched.get(index)
            enriched["tracking_state"] = "detected"
            enriched["is_predicted"] = False
            enriched["seconds_since_detection"] = 0.0
            output.append(enriched)

        # Draw short-gap predicted boxes for tracks not detected on this sample.
        # They exist for display/continuity only and must never become fresh
        # evidence in rule counters.
        for track in self._tracks.values():
            if track.track_id in used_track_ids:
                continue

            age = max(0.0, current_time - track.last_seen_seconds)
            hold = self._hold_seconds(track.class_name)
            if age > hold:
                continue

            predicted_bbox = self._predict_bbox(track, current_time, image_width, image_height)
            progress = min(1.0, age / hold)
            predicted_confidence = max(0.05, track.last_confidence * (1.0 - 0.55 * progress))
            track.predicted_frames += 1

            output.append({
                "class_id": track.class_id if track.class_id is not None else -1,
                "class_name": track.class_name,
                "confidence": round(predicted_confidence, 4),
                "bbox": predicted_bbox,
                "source": "tracker_prediction",
                "track_id": track.track_id,
                "tracking_state": "predicted",
                "is_predicted": True,
                "seconds_since_detection": round(age, 3),
            })

        return output

    def summaries(self) -> list[dict[str, Any]]:
        all_tracks = {**self._history, **self._tracks}
        return sorted(
            (track.as_dict() for track in all_tracks.values()),
            key=lambda item: (item["class_name"], item["track_id"]),
        )
