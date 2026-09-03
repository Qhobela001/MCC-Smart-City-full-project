from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class DeliveryOutboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingDelivery:
    path: Path
    payload: dict
    queued_at: str | None


class EvidenceDeliveryOutbox:
    """Durable at-least-once delivery queue stored beside evidence bundles.

    Each completed evidence event receives one ``delivery.json`` sidecar before
    any network submission is attempted. A backend outage or worker restart can
    therefore not silently discard the completed event. The backend's existing
    detection UUID idempotency makes retries safe.
    """

    def __init__(
        self,
        root: Path,
        camera_identifier: str,
        *,
        is_test: bool,
    ) -> None:
        self.root = root.resolve()
        self.namespace = "test" if is_test else "operational"
        self.camera_identifier = camera_identifier
        self.scope_root = (
            self.root / self.namespace / camera_identifier
        ).resolve()
        try:
            self.scope_root.relative_to(self.root)
        except ValueError as exc:
            raise DeliveryOutboxError("Invalid evidence outbox scope.") from exc
        self.scope_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".part")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _event_directory(self, detection_payload: dict) -> Path:
        snapshot_path = detection_payload.get("snapshot_path")
        if not isinstance(snapshot_path, str) or not snapshot_path.strip():
            raise DeliveryOutboxError(
                "Evidence delivery payload requires snapshot_path."
            )
        candidate = (self.root / snapshot_path).resolve().parent
        try:
            candidate.relative_to(self.scope_root)
        except ValueError as exc:
            raise DeliveryOutboxError(
                "Evidence delivery path is outside the configured camera scope."
            ) from exc
        return candidate

    def enqueue(self, detection_payload: dict) -> Path:
        detection_uuid = detection_payload.get("detection_uuid")
        if not isinstance(detection_uuid, str) or not detection_uuid.strip():
            raise DeliveryOutboxError(
                "Evidence delivery payload requires detection_uuid."
            )

        directory = self._event_directory(detection_payload)
        delivery_path = directory / "delivery.json"
        record = {
            "schema_version": 1,
            "status": "pending",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "detection_uuid": detection_uuid,
            "payload": detection_payload,
        }

        if delivery_path.is_file():
            try:
                existing = json.loads(delivery_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise DeliveryOutboxError(
                    f"Existing delivery record is unreadable: {delivery_path}"
                ) from exc
            if existing.get("detection_uuid") != detection_uuid:
                raise DeliveryOutboxError(
                    "Evidence directory already contains a different delivery."
                )
            return delivery_path

        self._atomic_json(delivery_path, record)
        return delivery_path

    def pending(self) -> list[PendingDelivery]:
        items: list[PendingDelivery] = []
        for path in sorted(self.scope_root.rglob("delivery.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise DeliveryOutboxError(
                    f"Delivery record is unreadable: {path}"
                ) from exc
            if record.get("status") != "pending":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                raise DeliveryOutboxError(
                    f"Delivery record has no payload: {path}"
                )
            items.append(
                PendingDelivery(
                    path=path,
                    payload=payload,
                    queued_at=record.get("queued_at"),
                )
            )
        return items

    def pending_count(self) -> int:
        return len(self.pending())

    def acknowledge(self, item: PendingDelivery) -> None:
        item.path.unlink(missing_ok=True)
