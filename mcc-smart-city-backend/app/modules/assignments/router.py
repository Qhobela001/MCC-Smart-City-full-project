from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.assignments import repository, service
from app.modules.assignments.models import AssignmentStatus
from app.modules.assignments.schemas import (
    AssignmentActivityRead,
    AssignmentCancel,
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentRead,
    AssignmentReject,
    AssignmentSubmit,
    AssignmentSummary,
    AssignmentUserSummary,
    AssignmentVerification,
)
from app.modules.users.models import User


router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.get("", response_model=AssignmentListResponse)
def list_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    assignment_status: AssignmentStatus | None = Query(default=None, alias="status"),
    department_id: int | None = None,
    assigned_user_id: int | None = None,
    incident_id: int | None = None,
    mine: bool = False,
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    items, total = repository.list_assignments(
        db, actor, page=page, page_size=page_size, status_value=assignment_status,
        department_id=department_id, assigned_user_id=assigned_user_id,
        incident_id=incident_id, mine=mine, search=search,
    )
    return service.to_list_response(db, items, total, page, page_size)


@router.get("/summary", response_model=AssignmentSummary)
def assignment_summary(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return service.summary_for_actor(db, actor)


@router.get("/assignees", response_model=list[AssignmentUserSummary])
def assignment_assignees(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return service.assignees_for_actor(db, actor, department_id)


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return service.assignment_to_read(db, service.create_assignment(db, actor, payload))


def _visible_or_404(db, actor, assignment_id):
    assignment = repository.get_visible(db, actor, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return service.assignment_to_read(db, _visible_or_404(db, actor, assignment_id))


@router.get("/{assignment_id}/timeline", response_model=list[AssignmentActivityRead])
def assignment_timeline(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return repository.list_activities(db, assignment.id)


@router.post("/{assignment_id}/accept", response_model=AssignmentRead)
def accept_assignment(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.accept_assignment(db, actor, assignment))


@router.post("/{assignment_id}/reject", response_model=AssignmentRead)
def reject_assignment(assignment_id: int, payload: AssignmentReject, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.reject_assignment(db, actor, assignment, payload.reason))


@router.post("/{assignment_id}/start", response_model=AssignmentRead)
def start_assignment(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.start_assignment(db, actor, assignment))


@router.post("/{assignment_id}/submit", response_model=AssignmentRead)
def submit_assignment(assignment_id: int, payload: AssignmentSubmit, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.submit_assignment(db, actor, assignment, payload))


@router.post("/{assignment_id}/verify", response_model=AssignmentRead)
def verify_assignment(assignment_id: int, payload: AssignmentVerification, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.verify_assignment(db, actor, assignment, approved=payload.approved, notes=payload.notes))


@router.post("/{assignment_id}/cancel", response_model=AssignmentRead)
def cancel_assignment(assignment_id: int, payload: AssignmentCancel, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    assignment = _visible_or_404(db, actor, assignment_id)
    return service.assignment_to_read(db, service.cancel_assignment(db, actor, assignment, payload.reason))
