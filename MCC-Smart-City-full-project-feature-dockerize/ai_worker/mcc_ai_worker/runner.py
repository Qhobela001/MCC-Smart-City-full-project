from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from .config import WorkerConfig
from .ingestion import IngestionClient
from .model import MCCModel, sha256_file
from .payloads import build_detection


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def iter_frames(path: Path, sample_seconds: float) -> Iterator[tuple[object, int, float]]:
    if path.suffix.lower() in IMAGE_SUFFIXES:
        yield str(path), 0, 0.0
        return
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"Unsupported source extension: {path.suffix}")

    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        capture.release()
        raise ValueError("Video reports an invalid frame rate.")
    interval = max(1, round(fps * sample_seconds))
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % interval == 0:
                yield frame, frame_index, frame_index / fps
            frame_index += 1
    finally:
        capture.release()


def write_health(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_source(
    config: WorkerConfig,
    source: Path,
    *,
    camera_identifier: str = "",
    stream_identifier: str = "",
    camera_head: str = "main",
    model: MCCModel | None = None,
    client: IngestionClient | None = None,
) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"Input source not found: {source}")
    source_digest = sha256_file(source)
    model = model or MCCModel(config.model_path, config.model_sha256)
    client = client or IngestionClient(
        config.backend_url, config.worker_key, config.request_attempts
    )
    started_at = datetime.now(timezone.utc)
    frames = detections_seen = detections_created = 0
    source_kind = "image" if source.suffix.lower() in IMAGE_SUFFIXES else "video"

    try:
        for frame, frame_index, offset_seconds in iter_frames(
            source, config.video_sample_seconds
        ):
            frames += 1
            raw = model.predict(frame, config.confidence, config.image_size)
            batch = [
                build_detection(
                    detection=item,
                    source_path=source,
                    source_digest=source_digest,
                    source_kind=source_kind,
                    frame_index=frame_index,
                    frame_time_seconds=offset_seconds,
                    detected_at=started_at + timedelta(seconds=offset_seconds),
                    camera_identifier=camera_identifier,
                    stream_identifier=stream_identifier,
                    camera_head=camera_head,
                    model_name=config.model_name,
                    model_version=config.model_version,
                    model_sha256=model.sha256,
                )
                for item in raw
            ]
            detections_seen += len(batch)
            response = client.submit(batch)
            detections_created += int(response.get("created", 0))

        health = {
            "status": "completed",
            "stage": "AI-1",
            "is_test": True,
            "source": source.name,
            "source_sha256": source_digest,
            "model_sha256": model.sha256,
            "frames_analyzed": frames,
            "detections_seen": detections_seen,
            "detections_created": detections_created,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        write_health(config.health_path, health)
        return health
    except Exception as exc:
        write_health(
            config.health_path,
            {
                "status": "failed",
                "stage": "AI-1",
                "error": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise
