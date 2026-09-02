from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


class EvidenceCaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncodedFrame:
    captured_at: datetime
    jpeg: bytes


@dataclass
class PendingEvidence:
    event_id: str
    detection: dict
    event_at: datetime
    frame_sequence: int
    directory: Path
    samples: list[EncodedFrame] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceBundle:
    detection: dict
    captured_at: datetime
    frame_sequence: int
    snapshot_path: str
    clip_path: str
    metadata: dict


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    if not cleaned:
        raise EvidenceCaptureError("Evidence path component is empty.")
    return cleaned[:100]


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(content)
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def default_encode_jpeg(frame: object, bbox: dict | None = None) -> bytes:
    import cv2

    image = frame.copy()
    if bbox:
        left = int(float(bbox["x1"]))
        top = int(float(bbox["y1"]))
        right = int(float(bbox["x2"]))
        bottom = int(float(bbox["y2"]))
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 3)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise EvidenceCaptureError("JPEG evidence encoding failed.")
    return encoded.tobytes()


def default_write_clip(path: Path, samples: list[EncodedFrame], fps: float) -> None:
    import cv2
    import numpy as np

    if not samples:
        raise EvidenceCaptureError("Cannot create an empty evidence clip.")
    first = cv2.imdecode(np.frombuffer(samples[0].jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if first is None:
        raise EvidenceCaptureError("Evidence clip frame decoding failed.")
    height, width = first.shape[:2]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".part.mp4")
    writer = cv2.VideoWriter(
        str(temporary), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise EvidenceCaptureError("Evidence MP4 writer could not be opened.")
    try:
        for sample in samples:
            frame = cv2.imdecode(
                np.frombuffer(sample.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if frame is None:
                continue
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))
            writer.write(frame)
    finally:
        writer.release()
    if not temporary.is_file() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise EvidenceCaptureError("Evidence MP4 encoding produced no data.")
    temporary.replace(path)


class EvidenceRecorder:
    def __init__(
        self,
        root: Path,
        camera_identifier: str,
        *,
        pre_seconds: float = 6.0,
        post_seconds: float = 6.0,
        sample_seconds: float = 0.5,
        retention_hours: float = 24.0,
        max_storage_bytes: int = 512 * 1024 * 1024,
        encode_jpeg: Callable[[object, dict | None], bytes] = default_encode_jpeg,
        write_clip: Callable[[Path, list[EncodedFrame], float], None] = default_write_clip,
        is_test: bool = True,
    ) -> None:
        self.root = root.resolve()
        self.camera_identifier = _safe_component(camera_identifier)
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.sample_seconds = sample_seconds
        self.retention_hours = retention_hours
        self.max_storage_bytes = max_storage_bytes
        self.encode_jpeg = encode_jpeg
        self.write_clip = write_clip
        self.is_test = is_test
        self.buffer: deque[EncodedFrame] = deque()
        self.pending: list[PendingEvidence] = []
        self.last_sample_at: datetime | None = None
        self.root.mkdir(parents=True, exist_ok=True)
        self.enforce_retention(datetime.now(timezone.utc))

    def add_frame(self, frame: object, captured_at: datetime) -> None:
        if self.last_sample_at is not None:
            if (captured_at - self.last_sample_at).total_seconds() < self.sample_seconds:
                return
        sample = EncodedFrame(captured_at, self.encode_jpeg(frame, None))
        self.last_sample_at = captured_at
        self.buffer.append(sample)
        cutoff = captured_at - timedelta(seconds=self.pre_seconds)
        while self.buffer and self.buffer[0].captured_at < cutoff:
            self.buffer.popleft()
        for pending in self.pending:
            if captured_at > pending.event_at:
                pending.samples.append(sample)

    def start(
        self, detection: dict, frame: object, captured_at: datetime, frame_sequence: int
    ) -> str:
        qualification = detection.get("qualification") or {}
        identity = json.dumps({
            "camera": self.camera_identifier,
            "captured_at": captured_at.isoformat(),
            "track_id": qualification.get("track_id"),
            "event_type": qualification.get("event_type"),
        }, sort_keys=True)
        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
        day = captured_at.astimezone(timezone.utc).strftime("%Y/%m/%d")
        namespace = "test" if self.is_test else "operational"
        directory = self.root / namespace / self.camera_identifier / day / event_id
        directory.resolve().relative_to(self.root)
        snapshot = directory / "snapshot.jpg"
        _atomic_write(snapshot, self.encode_jpeg(frame, detection.get("bbox")))
        self.pending.append(PendingEvidence(
            event_id=event_id,
            detection=detection,
            event_at=captured_at,
            frame_sequence=frame_sequence,
            directory=directory,
            samples=list(self.buffer),
        ))
        return event_id

    def complete_ready(
        self, now: datetime, *, force: bool = False
    ) -> list[EvidenceBundle]:
        ready = [
            item for item in self.pending
            if force or now >= item.event_at + timedelta(seconds=self.post_seconds)
        ]
        self.pending = [item for item in self.pending if item not in ready]
        completed = [self._finalize(item, force=force) for item in ready]
        if completed:
            protected = {
                (self.root / item.snapshot_path).parent.resolve()
                for item in completed
            }
            try:
                self.enforce_retention(now, protected=protected)
            except Exception:
                for directory in protected:
                    shutil.rmtree(directory, ignore_errors=True)
                raise
        return completed

    def _finalize(self, pending: PendingEvidence, *, force: bool) -> EvidenceBundle:
        snapshot = pending.directory / "snapshot.jpg"
        clip = pending.directory / "clip.mp4"
        fps = max(1.0, 1.0 / self.sample_seconds)
        self.write_clip(clip, pending.samples, fps)
        snapshot_hash = _sha256(snapshot)
        clip_hash = _sha256(clip)
        relative_snapshot = snapshot.relative_to(self.root).as_posix()
        relative_clip = clip.relative_to(self.root).as_posix()
        metadata = {
            "event_id": pending.event_id,
            "stage": "AI-5" if not self.is_test else "AI-4",
            "is_test": self.is_test,
            "camera_identifier": self.camera_identifier,
            "captured_at": pending.event_at.isoformat(),
            "pre_seconds": self.pre_seconds,
            "post_seconds": self.post_seconds,
            "sample_seconds": self.sample_seconds,
            "clip_frame_count": len(pending.samples),
            "post_window_truncated": force,
            "snapshot": {
                "path": relative_snapshot,
                "sha256": snapshot_hash,
                "size_bytes": snapshot.stat().st_size,
                "mime_type": "image/jpeg",
            },
            "clip": {
                "path": relative_clip,
                "sha256": clip_hash,
                "size_bytes": clip.stat().st_size,
                "mime_type": "video/mp4",
            },
        }
        _atomic_write(
            pending.directory / "manifest.json",
            json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8"),
        )
        return EvidenceBundle(
            detection=pending.detection,
            captured_at=pending.event_at,
            frame_sequence=pending.frame_sequence,
            snapshot_path=relative_snapshot,
            clip_path=relative_clip,
            metadata=metadata,
        )

    def enforce_retention(
        self, now: datetime, *, protected: set[Path] | None = None
    ) -> None:
        protected = protected or set()
        cutoff = now.timestamp() - self.retention_hours * 3600
        event_directories = {
            path.parent.resolve() for path in self.root.rglob("manifest.json")
        }
        for directory in list(event_directories):
            newest = max(
                (path.stat().st_mtime for path in directory.rglob("*") if path.is_file()),
                default=0,
            )
            if newest < cutoff and directory not in protected:
                shutil.rmtree(directory, ignore_errors=True)
                event_directories.discard(directory)

        def directory_size(directory: Path) -> int:
            return sum(
                path.stat().st_size for path in directory.rglob("*") if path.is_file()
            )

        ordered = sorted(
            event_directories,
            key=lambda directory: max(
                (path.stat().st_mtime for path in directory.rglob("*") if path.is_file()),
                default=0,
            ),
        )
        total = sum(directory_size(directory) for directory in ordered)
        for directory in ordered:
            if total <= self.max_storage_bytes:
                break
            if directory in protected:
                continue
            size = directory_size(directory)
            shutil.rmtree(directory, ignore_errors=True)
            total -= size
        if total > self.max_storage_bytes:
            raise EvidenceCaptureError(
                "New evidence bundle exceeds the configured storage limit."
            )
