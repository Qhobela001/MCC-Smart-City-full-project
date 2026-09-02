from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


DETECTION_TYPES = {
    "trash": "illegal_dumping",
    "bag": "illegal_dumping",
    "waste_skip": "skip_overflow",
    "vehicle_smoke": "vehicle_smoke_emission",
    "pothole": "pothole",
    "road_crack": "road_damage",
    "person": "other",
    "car": "other",
    "license_plate": "other",
    "broom": "other",
}


def stable_detection_uuid(
    *, source_digest: str, frame_index: int, detection: dict, model_sha256: str
) -> str:
    identity = json.dumps(
        {
            "source": source_digest,
            "frame": frame_index,
            "class": detection["class_name"],
            "bbox": detection["bbox"],
            "model": model_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


def stable_live_detection_uuid(
    *,
    camera_identifier: str,
    gateway_path: str,
    captured_at: datetime,
    frame_sequence: int,
    detection: dict,
    model_sha256: str,
) -> str:
    identity = json.dumps(
        {
            "camera": camera_identifier,
            "path": gateway_path,
            "captured_at": captured_at.astimezone(timezone.utc).isoformat(),
            "frame_sequence": frame_sequence,
            "class": detection["class_name"],
            "bbox": detection["bbox"],
            "model": model_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


def build_live_detection(
    *,
    detection: dict,
    captured_at: datetime,
    camera_identifier: str,
    gateway_path: str,
    frame_sequence: int,
    model_name: str,
    model_version: str,
    model_sha256: str,
) -> dict:
    return {
        "detection_uuid": stable_live_detection_uuid(
            camera_identifier=camera_identifier,
            gateway_path=gateway_path,
            captured_at=captured_at,
            frame_sequence=frame_sequence,
            detection=detection,
            model_sha256=model_sha256,
        ),
        "detection_type": DETECTION_TYPES[detection["class_name"]],
        "class_name": detection["class_name"],
        "confidence": round(float(detection["confidence"]), 6),
        "detected_at": captured_at.astimezone(timezone.utc).isoformat(),
        "source_type": "test",
        "camera_identifier": camera_identifier,
        "stream_identifier": gateway_path,
        "model_name": model_name,
        "model_version": model_version,
        "object_count": 1,
        "attributes": {
            "bbox_xyxy": detection["bbox"],
            "class_id": detection["class_id"],
            "camera_head": "composite",
            "source_kind": "live_rtsp",
            "gateway_path": gateway_path,
            "frame_sequence": frame_sequence,
            "model_sha256": model_sha256,
            "stage": "AI-2",
            "observation_mode": True,
        },
        # AI-2 remains observation-only regardless of environment settings.
        "is_test": True,
    }


def build_detection(
    *,
    detection: dict,
    source_path: Path,
    source_digest: str,
    source_kind: str,
    frame_index: int,
    frame_time_seconds: float,
    detected_at: datetime,
    camera_identifier: str,
    stream_identifier: str,
    camera_head: str,
    model_name: str,
    model_version: str,
    model_sha256: str,
) -> dict:
    return {
        "detection_uuid": stable_detection_uuid(
            source_digest=source_digest,
            frame_index=frame_index,
            detection=detection,
            model_sha256=model_sha256,
        ),
        "detection_type": DETECTION_TYPES[detection["class_name"]],
        "class_name": detection["class_name"],
        "confidence": round(float(detection["confidence"]), 6),
        "detected_at": detected_at.astimezone(timezone.utc).isoformat(),
        "source_type": "test",
        "camera_identifier": camera_identifier or None,
        "stream_identifier": stream_identifier or None,
        "model_name": model_name,
        "model_version": model_version,
        "object_count": 1,
        "attributes": {
            "bbox_xyxy": detection["bbox"],
            "class_id": detection["class_id"],
            "camera_head": camera_head,
            "source_file": source_path.name,
            "source_kind": source_kind,
            "source_sha256": source_digest,
            "frame_index": frame_index,
            "frame_time_seconds": round(frame_time_seconds, 3),
            "model_sha256": model_sha256,
            "stage": "AI-1",
        },
        # AI-1 is intentionally incapable of creating operational incidents.
        "is_test": True,
    }
