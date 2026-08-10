from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.modules.assignments.models import AssignmentStatus
from app.modules.incidents.models import IncidentPriority


class AssignmentUserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    employee_number: str | None = None
    department_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class AssignmentDepartmentSummary(BaseModel):
    id: int
    name: str
    code: str
    model_config = ConfigDict(from_attributes=True)


class AssignmentIncidentSummary(BaseModel):
    id: int
    incident_number: str
    title: str
    incident_type: str
    priority: str
    status: str
    location_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


class AssignmentEvidenceSummary(BaseModel):
    id: int
    original_file_name: str
    evidence_type: str
    mime_type: str
    file_size_bytes: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    incident_id: int
    assigned_user_id: int
    department_id: int | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    instructions: str | None = Field(default=None, max_length=5000)
    priority: IncidentPriority | None = None
    due_at: datetime | None = None


class AssignmentReject(BaseModel):
    reason: str = Field(min_length=3, max_length=3000)


class AssignmentSubmit(BaseModel):
    completion_notes: str = Field(min_length=3, max_length=5000)
    evidence_ids: list[int] = Field(min_length=1)


class AssignmentVerification(BaseModel):
    approved: bool
    notes: str = Field(min_length=3, max_length=5000)


class AssignmentCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=3000)


class AssignmentActivityRead(BaseModel):
    id: int
    assignment_id: int
    actor_user_id: int
    action: str
    previous_status: AssignmentStatus | None
    new_status: AssignmentStatus | None
    notes: str | None
    actor: AssignmentUserSummary
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssignmentRead(BaseModel):
    id: int
    assignment_number: str
    incident_id: int
    department_id: int
    assigned_user_id: int
    assigned_by_id: int
    title: str
    instructions: str | None
    priority: str
    status: AssignmentStatus
    due_at: datetime | None
    accepted_at: datetime | None
    started_at: datetime | None
    submitted_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    completion_notes: str | None
    verification_notes: str | None
    rejection_reason: str | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    incident: AssignmentIncidentSummary
    department: AssignmentDepartmentSummary
    assigned_user: AssignmentUserSummary
    assigned_by: AssignmentUserSummary
    evidence: list[AssignmentEvidenceSummary] = []
    model_config = ConfigDict(from_attributes=True)


class AssignmentListResponse(BaseModel):
    items: list[AssignmentRead]
    total: int
    page: int
    page_size: int
    pages: int


class AssignmentSummary(BaseModel):
    total_visible: int
    my_open: int
    pending_acceptance: int
    in_progress: int
    awaiting_verification: int
    overdue: int
    completed: int
