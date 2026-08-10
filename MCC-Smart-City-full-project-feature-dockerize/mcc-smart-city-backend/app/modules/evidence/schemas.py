from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.evidence.models import EvidenceType
from app.modules.incidents.schemas import UserSummary


class EvidenceRead(BaseModel):
    id: int
    incident_id: int
    uploaded_by_id: int
    uploaded_by: UserSummary

    evidence_type: EvidenceType
    original_file_name: str
    stored_file_name: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str

    description: str | None
    captured_at: datetime | None
    latitude: float | None
    longitude: float | None

    is_anonymized: bool
    is_enforcement_evidence: bool
    created_at: datetime

    download_url: str

    model_config = ConfigDict(from_attributes=True)


class EvidenceMetadataUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=3000)
    captured_at: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_anonymized: bool | None = None
    is_enforcement_evidence: bool | None = None

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            if self.latitude is not None or self.longitude is not None:
                raise ValueError(
                    "Latitude and longitude must be supplied together."
                )
        return self
