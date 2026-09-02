import hashlib
import json
import math
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.ai_detections import repository
from app.modules.ai_detections.models import (
    AIDetection,
    DetectionReviewStatus,
)
from app.modules.alerts import service as alert_service
from app.modules.evidence import repository as evidence_repository
from app.modules.evidence.models import Evidence, EvidenceType
from app.modules.ai_detections.schemas import (
    AIDetectionBatchCreate,
    AIDetectionBatchResponse,
    AIDetectionCreate,
    AIDetectionListResponse,
    AIDetectionRead,
)
from app.modules.incident_engine import (
    service as incident_engine_service,
)
from app.modules.incident_engine import rules as incident_rules
from app.modules.incidents import repository as incident_repository
from app.modules.incidents.models import Incident, IncidentActivity, IncidentPriority, IncidentSource, IncidentStatus, IncidentType
from app.modules.incidents.service import generate_incident_number, validate_department
from app.modules.users.models import User
from app.core.deps import user_has_permission


AI_EVIDENCE_STAGING_ROOT = Path(
    os.getenv("AI_EVIDENCE_STAGING_DIR", "/ai-evidence")
).resolve()
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()


def create_detection(
    db: Session,
    payload: AIDetectionCreate,
    *,
    actor: User,
) -> AIDetection:
    if payload.detection_uuid:
        existing = repository.get_detection_by_uuid(
            db,
            payload.detection_uuid,
        )

        if existing:
            return existing

    try:
        # Do not commit here yet.
        # Detection + incident + alert must succeed
        # or fail together.
        detection = repository.create_detection(
            db,
            payload,
            commit=False,
        )

        incident_engine_service.process_detection(
            db,
            detection,
            actor=actor,
        )

        db.commit()
        db.refresh(detection)

        return detection

    except IntegrityError:
        db.rollback()

        if payload.detection_uuid:
            existing = repository.get_detection_by_uuid(
                db,
                payload.detection_uuid,
            )

            if existing:
                return existing

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Detection could not be persisted "
                "because of a database conflict."
            ),
        )

    except Exception:
        db.rollback()
        raise


def create_detection_batch(
    db: Session,
    payload: AIDetectionBatchCreate,
    *,
    actor: User,
) -> AIDetectionBatchResponse:
    unique_payloads: list[AIDetectionCreate] = []
    existing_items: list[AIDetection] = []

    seen_uuids: set[str] = set()

    for item in payload.detections:
        if item.detection_uuid:
            if item.detection_uuid in seen_uuids:
                continue

            seen_uuids.add(item.detection_uuid)

            existing = repository.get_detection_by_uuid(
                db,
                item.detection_uuid,
            )

            if existing:
                existing_items.append(existing)
                continue

        unique_payloads.append(item)

    try:
        created_items = repository.create_detection_batch(
            db,
            unique_payloads,
            commit=False,
        )

        for detection in created_items:
            incident_engine_service.process_detection(
                db,
                detection,
                actor=actor,
            )

        db.commit()

        for detection in created_items:
            db.refresh(detection)

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "One or more detections could not be "
                "persisted because of a database conflict."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise

    items = existing_items + created_items

    return AIDetectionBatchResponse(
        created=len(created_items),
        items=[
            AIDetectionRead.model_validate(item)
            for item in items
        ],
    )


def get_detection_or_404(
    db: Session,
    detection_id: int,
) -> AIDetection:
    detection = repository.get_detection(
        db,
        detection_id,
    )

    if detection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI detection not found.",
        )

    return detection


def review_detection(
    db: Session,
    detection: AIDetection,
    *,
    review_status: DetectionReviewStatus,
    notes: str,
    department_id: int | None,
    priority: IncidentPriority | None,
    actor: User,
) -> AIDetection:
    detection = repository.lock_detection(db, detection.id) or detection
    if detection.review_status != DetectionReviewStatus.unreviewed:
        raise HTTPException(status_code=409, detail="This AI detection has already been reviewed.")

    now = datetime.now(timezone.utc)
    attributes = dict(detection.attributes or {})
    attributes["human_review"] = {
        "decision": review_status.value,
        "notes": notes,
        "reviewed_by_id": actor.id,
        "reviewed_at": now.isoformat(),
    }

    if review_status == DetectionReviewStatus.rejected:
        detection.attributes = attributes
        repository.review_detection(
            db, detection, review_status=review_status,
            reviewed_by_id=actor.id, reviewed_at=now,
        )
        db.commit()
        db.refresh(detection)
        return detection

    # Test data can be reviewed and rejected, but can never enter operations.
    if detection.is_test or detection.source_type.value == "test":
        raise HTTPException(
            status_code=409,
            detail="Test detections cannot be promoted to operational incidents.",
        )
    if detection.source_type.value != "camera":
        raise HTTPException(status_code=409, detail="Only production camera detections can be promoted.")
    if not user_has_permission(actor, "ai_detections.promote"):
        raise HTTPException(status_code=403, detail="Permission required: ai_detections.promote")
    if detection.incident_id is not None:
        raise HTTPException(status_code=409, detail="Detection is already linked to an incident.")
    if not detection.camera_identifier:
        raise HTTPException(status_code=422, detail="Camera identifier is required for promotion.")

    validate_department(db, department_id)
    manifest, staged_files = _validated_staged_bundle(detection)
    created_paths: list[Path] = []
    try:
        rule = incident_rules.get_rule(detection)
        incident = Incident(
            incident_number=generate_incident_number(),
            incident_type=IncidentType(detection.detection_type.value),
            title=incident_rules.incident_title(detection),
            description=incident_rules.incident_description(detection),
            priority=priority or incident_rules.priority_for_detection(detection, rule),
            status=IncidentStatus.new,
            source=IncidentSource.ai_detection,
            department_id=department_id,
            created_by_id=actor.id,
            gis_location_id=detection.gis_location_id,
            location_name=detection.location_name,
            latitude=detection.latitude,
            longitude=detection.longitude,
            is_ai_generated=True,
            reported_at=detection.detected_at,
        )
        incident_repository.create(db, incident)
        db.flush()

        destination = UPLOAD_ROOT / "evidence" / str(incident.id)
        destination.mkdir(parents=True, exist_ok=True)
        for kind, source, metadata in staged_files:
            suffix = ".jpg" if kind == "snapshot" else ".mp4"
            stored_name = f"ai-{detection.detection_uuid}-{kind}{suffix}"
            target = destination / stored_name
            temporary = target.with_suffix(target.suffix + ".part")
            shutil.copyfile(source, temporary)
            temporary.replace(target)
            created_paths.append(target)
            evidence_repository.create(db, Evidence(
                incident_id=incident.id,
                uploaded_by_id=actor.id,
                evidence_type=(EvidenceType.image if kind == "snapshot" else EvidenceType.video),
                original_file_name=stored_name,
                stored_file_name=stored_name,
                relative_path=target.relative_to(UPLOAD_ROOT).as_posix(),
                mime_type=metadata["mime_type"],
                file_size_bytes=metadata["size_bytes"],
                sha256_hash=metadata["sha256"],
                description=f"AI-captured {kind} for detection {detection.detection_uuid}.",
                captured_at=detection.detected_at,
                latitude=detection.latitude,
                longitude=detection.longitude,
                is_anonymized=False,
                is_enforcement_evidence=True,
            ))

        detection.incident_id = incident.id
        detection.attributes = attributes | {
            "promotion": {
                "status": "promoted",
                "incident_id": incident.id,
                "evidence_event_id": manifest.get("event_id"),
                "promoted_at": now.isoformat(),
            }
        }
        repository.review_detection(
            db, detection, review_status=DetectionReviewStatus.confirmed,
            reviewed_by_id=actor.id, reviewed_at=now,
        )
        incident_repository.add_activity(db, IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action="incident.ai_review_approved",
            previous_status=None,
            new_status=IncidentStatus.new,
            notes=f"Approved AI detection {detection.detection_uuid}. Review: {notes}",
        ))
        db.flush()
        db.refresh(incident)
        alert_service.notify_incident_created(db, incident=incident, actor=actor)
        db.commit()
        db.refresh(detection)
        return detection
    except HTTPException:
        db.rollback()
        _remove_created_files(created_paths)
        raise
    except Exception:
        db.rollback()
        _remove_created_files(created_paths)
        raise


def _remove_created_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _safe_staged_path(relative_path: str) -> Path:
    candidate = (AI_EVIDENCE_STAGING_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(AI_EVIDENCE_STAGING_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid staged evidence path.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=409, detail="Staged AI evidence is unavailable or expired.")
    return candidate


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_staged_bundle(detection: AIDetection):
    evidence = (detection.attributes or {}).get("evidence")
    if not isinstance(evidence, dict):
        raise HTTPException(status_code=409, detail="Detection has no completed evidence manifest.")
    if evidence.get("is_test") is True:
        raise HTTPException(status_code=409, detail="Test evidence cannot be promoted.")
    staged_files = []
    for kind, expected_path in (("snapshot", detection.snapshot_path), ("clip", detection.clip_path)):
        metadata = evidence.get(kind)
        if not expected_path or not isinstance(metadata, dict) or metadata.get("path") != expected_path:
            raise HTTPException(status_code=409, detail=f"Incomplete {kind} evidence metadata.")
        if not expected_path.startswith("operational/"):
            raise HTTPException(status_code=409, detail="Only operational evidence can be promoted.")
        path = _safe_staged_path(expected_path)
        if path.stat().st_size != metadata.get("size_bytes") or _hash(path) != metadata.get("sha256"):
            raise HTTPException(status_code=409, detail=f"Staged {kind} failed integrity verification.")
        staged_files.append((kind, path, metadata))
    return evidence, staged_files


def get_staged_evidence_file(detection: AIDetection, *, kind: str):
    if kind not in {"snapshot", "clip"}:
        raise HTTPException(status_code=404, detail="Evidence kind not found.")
    _, files = _validated_staged_bundle_for_preview(detection)
    selected = next(item for item in files if item[0] == kind)
    return selected[1], selected[2]["mime_type"], selected[1].name


def _validated_staged_bundle_for_preview(detection: AIDetection):
    evidence = (detection.attributes or {}).get("evidence")
    if not isinstance(evidence, dict):
        raise HTTPException(status_code=404, detail="Staged evidence not found.")
    staged_files = []
    for kind, relative in (("snapshot", detection.snapshot_path), ("clip", detection.clip_path)):
        metadata = evidence.get(kind)
        if not relative or not isinstance(metadata, dict) or metadata.get("path") != relative:
            raise HTTPException(status_code=404, detail="Staged evidence not found.")
        path = _safe_staged_path(relative)
        if path.stat().st_size != metadata.get("size_bytes") or _hash(path) != metadata.get("sha256"):
            raise HTTPException(status_code=409, detail=f"Staged {kind} failed integrity verification.")
        staged_files.append((kind, path, metadata))
    return evidence, staged_files


def to_read(
    detection: AIDetection,
) -> AIDetectionRead:
    return AIDetectionRead.model_validate(detection)


def to_list_response(
    items: list[AIDetection],
    total: int,
    page: int,
    page_size: int,
) -> AIDetectionListResponse:
    pages = (
        math.ceil(total / page_size)
        if total > 0
        else 0
    )

    return AIDetectionListResponse(
        items=[
            AIDetectionRead.model_validate(item)
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
