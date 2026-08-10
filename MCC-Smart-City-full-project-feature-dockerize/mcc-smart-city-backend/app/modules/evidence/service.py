import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from secrets import token_hex

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import user_has_permission
from app.modules.alerts import service as alert_service
from app.modules.evidence import repository
from app.modules.evidence.models import Evidence, EvidenceType
from app.modules.evidence.schemas import (
    EvidenceMetadataUpdate,
    EvidenceRead,
)
from app.modules.incidents.models import (
    Incident,
    IncidentActivity,
    IncidentStatus,
)
from app.modules.incidents.repository import add_activity
from app.modules.users.models import User


UPLOAD_ROOT = Path(
    os.getenv("UPLOAD_DIR", "uploads")
).resolve()
MAX_EVIDENCE_SIZE = int(
    os.getenv(
        "MAX_EVIDENCE_SIZE_BYTES",
        str(25 * 1024 * 1024),
    )
)


ALLOWED_MIME_TYPES: dict[str, EvidenceType] = {
    "image/jpeg": EvidenceType.image,
    "image/png": EvidenceType.image,
    "image/webp": EvidenceType.image,
    "video/mp4": EvidenceType.video,
    "video/webm": EvidenceType.video,
    "audio/mpeg": EvidenceType.audio,
    "audio/wav": EvidenceType.audio,
    "application/pdf": EvidenceType.document,
}


def ensure_can_access_evidence(
    actor: User,
    incident: Incident,
) -> None:
    if actor.is_superuser:
        return

    if user_has_permission(actor, "evidence.view"):
        return

    if (
        incident.created_by_id == actor.id
        or incident.assigned_user_id == actor.id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorised to access this evidence.",
    )


def ensure_can_upload(
    actor: User,
    incident: Incident,
) -> None:
    if actor.is_superuser:
        return

    if user_has_permission(actor, "evidence.upload"):
        return

    if (
        incident.created_by_id == actor.id
        or incident.assigned_user_id == actor.id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorised to upload evidence.",
    )


def ensure_can_delete(
    actor: User,
    evidence: Evidence,
) -> None:
    if actor.is_superuser:
        return

    if user_has_permission(actor, "evidence.delete"):
        return

    if evidence.uploaded_by_id == actor.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorised to delete this evidence.",
    )


def validate_file(upload: UploadFile) -> EvidenceType:
    content_type = (
        upload.content_type or "application/octet-stream"
    ).lower()

    evidence_type = ALLOWED_MIME_TYPES.get(content_type)

    if evidence_type is None:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed MIME types: {allowed}",
        )

    return evidence_type


def create_storage_path(
    incident_id: int,
    original_name: str,
) -> tuple[Path, str, str]:
    suffix = Path(original_name).suffix.lower()
    stored_name = (
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        f"-{token_hex(8)}{suffix}"
    )

    relative_directory = Path("evidence") / str(incident_id)
    absolute_directory = UPLOAD_ROOT / relative_directory
    absolute_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    relative_path = (
        relative_directory / stored_name
    ).as_posix()

    return (
        absolute_directory / stored_name,
        stored_name,
        relative_path,
    )


def save_upload(
    db: Session,
    actor: User,
    incident: Incident,
    upload: UploadFile,
    *,
    description: str | None,
    captured_at: datetime | None,
    latitude: float | None,
    longitude: float | None,
    is_anonymized: bool,
    is_enforcement_evidence: bool,
) -> Evidence:
    ensure_can_upload(actor, incident)

    if incident.status in {
        IncidentStatus.resolved,
        IncidentStatus.dismissed,
    } and not actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence cannot be added to a closed incident.",
        )

    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and longitude must be supplied together.",
        )

    evidence_type = validate_file(upload)

    original_name = (
        Path(upload.filename or "evidence").name
    )

    (
        absolute_path,
        stored_name,
        relative_path,
    ) = create_storage_path(
        incident.id,
        original_name,
    )

    sha256 = hashlib.sha256()
    file_size = 0

    try:
        with absolute_path.open("wb") as destination:
            while chunk := upload.file.read(1024 * 1024):
                file_size += len(chunk)

                if file_size > MAX_EVIDENCE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "Evidence file exceeds the configured "
                            "maximum size."
                        ),
                    )

                sha256.update(chunk)
                destination.write(chunk)

        evidence = Evidence(
            incident_id=incident.id,
            uploaded_by_id=actor.id,
            evidence_type=evidence_type,
            original_file_name=original_name,
            stored_file_name=stored_name,
            relative_path=relative_path,
            mime_type=(
                upload.content_type
                or "application/octet-stream"
            ),
            file_size_bytes=file_size,
            sha256_hash=sha256.hexdigest(),
            description=description,
            captured_at=captured_at,
            latitude=latitude,
            longitude=longitude,
            is_anonymized=is_anonymized,
            is_enforcement_evidence=is_enforcement_evidence,
        )

        repository.create(db, evidence)

        add_activity(
            db,
            IncidentActivity(
                incident_id=incident.id,
                actor_user_id=actor.id,
                action="evidence.uploaded",
                previous_status=incident.status,
                new_status=incident.status,
                notes=f"Uploaded evidence: {original_name}",
            ),
        )

        alert_service.notify_evidence_uploaded(
            db,
            incident=incident,
            actor=actor,
            original_file_name=original_name,
        )

        db.commit()
        db.refresh(evidence)
        return evidence

    except Exception:
        if absolute_path.exists():
            absolute_path.unlink(missing_ok=True)
        raise

    finally:
        upload.file.close()


def update_metadata(
    db: Session,
    actor: User,
    incident: Incident,
    evidence: Evidence,
    payload: EvidenceMetadataUpdate,
) -> Evidence:
    ensure_can_upload(actor, incident)

    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(evidence, field_name, value)

    repository.save(db, evidence)

    add_activity(
        db,
        IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action="evidence.updated",
            previous_status=incident.status,
            new_status=incident.status,
            notes=(
                f"Updated evidence metadata: "
                f"{evidence.original_file_name}"
            ),
        ),
    )

    db.commit()
    db.refresh(evidence)
    return evidence


def delete_evidence(
    db: Session,
    actor: User,
    incident: Incident,
    evidence: Evidence,
) -> None:
    ensure_can_delete(actor, evidence)

    absolute_path = (
        UPLOAD_ROOT / evidence.relative_path
    ).resolve()

    try:
        absolute_path.relative_to(UPLOAD_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid stored evidence path.",
        ) from exc

    original_name = evidence.original_file_name

    repository.delete(db, evidence)

    add_activity(
        db,
        IncidentActivity(
            incident_id=incident.id,
            actor_user_id=actor.id,
            action="evidence.deleted",
            previous_status=incident.status,
            new_status=incident.status,
            notes=f"Deleted evidence: {original_name}",
        ),
    )

    db.commit()

    if absolute_path.exists():
        absolute_path.unlink(missing_ok=True)


def absolute_file_path(evidence: Evidence) -> Path:
    path = (
        UPLOAD_ROOT / evidence.relative_path
    ).resolve()

    try:
        path.relative_to(UPLOAD_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid stored evidence path.",
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file is missing from storage.",
        )

    return path


def to_read(evidence: Evidence) -> EvidenceRead:
    data = EvidenceRead.model_validate(evidence)
    data.download_url = (
        f"/api/v1/evidence/{evidence.id}/download"
    )
    return data
