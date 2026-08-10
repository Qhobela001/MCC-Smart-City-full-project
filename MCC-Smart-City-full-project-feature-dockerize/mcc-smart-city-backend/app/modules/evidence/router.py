from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import (
    get_current_user,
    get_db,
    require_permission,
)
from app.modules.evidence import repository, service
from app.modules.evidence.schemas import (
    EvidenceMetadataUpdate,
    EvidenceRead,
)
from app.modules.incidents import repository as incident_repository
from app.modules.users.models import User


router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


@router.get(
    "/incidents/{incident_id}",
    response_model=list[EvidenceRead],
)
def list_incident_evidence(
    incident_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> list[EvidenceRead]:
    incident = incident_repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    service.ensure_can_access_evidence(
        actor,
        incident,
    )

    evidence_items = repository.list_for_incident(
        db,
        incident.id,
    )

    return [
        service.to_read(item)
        for item in evidence_items
    ]


@router.post(
    "/incidents/{incident_id}",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_incident_evidence(
    incident_id: int,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    captured_at: datetime | None = Form(default=None),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    is_anonymized: bool = Form(default=False),
    is_enforcement_evidence: bool = Form(default=True),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> EvidenceRead:
    incident = incident_repository.get_visible(
        db,
        actor,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    evidence = service.save_upload(
        db,
        actor,
        incident,
        file,
        description=description,
        captured_at=captured_at,
        latitude=latitude,
        longitude=longitude,
        is_anonymized=is_anonymized,
        is_enforcement_evidence=is_enforcement_evidence,
    )

    return service.to_read(evidence)


@router.patch(
    "/{evidence_id}",
    response_model=EvidenceRead,
)
def update_evidence_metadata(
    evidence_id: int,
    payload: EvidenceMetadataUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> EvidenceRead:
    evidence = repository.get(db, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    incident = incident_repository.get_visible(
        db,
        actor,
        evidence.incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    updated = service.update_metadata(
        db,
        actor,
        incident,
        evidence,
        payload,
    )

    return service.to_read(updated)


@router.get(
    "/{evidence_id}/download",
)
def download_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    evidence = repository.get(db, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    incident = incident_repository.get_visible(
        db,
        actor,
        evidence.incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    service.ensure_can_access_evidence(
        actor,
        incident,
    )

    path = service.absolute_file_path(evidence)

    return FileResponse(
        path=path,
        media_type=evidence.mime_type,
        filename=evidence.original_file_name,
    )


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> Response:
    evidence = repository.get(db, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    incident = incident_repository.get_visible(
        db,
        actor,
        evidence.incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    service.delete_evidence(
        db,
        actor,
        incident,
        evidence,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
