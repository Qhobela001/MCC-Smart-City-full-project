from datetime import datetime, timezone
from math import ceil
from secrets import token_hex

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import user_has_permission
from app.modules.alerts import service as alert_service
from app.modules.assignments import repository
from app.modules.assignments.models import Assignment, AssignmentActivity, AssignmentEvidenceLink, AssignmentStatus
from app.modules.assignments.schemas import AssignmentCreate, AssignmentListResponse, AssignmentRead, AssignmentSubmit, AssignmentSummary
from app.modules.departments.models import Department
from app.modules.incidents import repository as incident_repository
from app.modules.incidents.models import Incident, IncidentActivity, IncidentStatus
from app.modules.users.models import User


TERMINAL_ASSIGNMENT_STATUSES = {
    AssignmentStatus.completed,
    AssignmentStatus.rejected,
    AssignmentStatus.cancelled,
}


def generate_assignment_number() -> str:
    return f"MCC-ASG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{token_hex(3).upper()}"


def _validate_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    if not department.is_active:
        raise HTTPException(status_code=400, detail="The selected department is inactive.")
    return department


def _validate_assignee(db: Session, user_id: int, department_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Assigned user not found.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="The selected employee account is inactive.")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="A SuperAdmin account cannot receive an operational assignment.")
    if user.department_id != department_id:
        raise HTTPException(status_code=400, detail="The assigned employee must belong to the selected department.")
    return user


def _ensure_creation_scope(actor: User, department_id: int) -> None:
    if actor.is_superuser:
        return
    if not (
        user_has_permission(actor, "assignments.create")
        or user_has_permission(actor, "incidents.assign")
    ):
        raise HTTPException(
            status_code=403,
            detail="Permission required: assignments.create or incidents.assign",
        )
    if user_has_permission(actor, "assignments.manage_all") or user_has_permission(actor, "assignments.view_all"):
        return
    if actor.department_id != department_id:
        raise HTTPException(status_code=403, detail="You may create assignments only for your department.")


def _ensure_management_scope(actor: User, assignment: Assignment) -> None:
    if actor.is_superuser or user_has_permission(actor, "assignments.manage_all"):
        return
    if user_has_permission(actor, "assignments.manage_department") and actor.department_id == assignment.department_id:
        return
    if assignment.assigned_by_id == actor.id:
        return
    raise HTTPException(status_code=403, detail="You are not authorised to manage this assignment.")


def _ensure_verification_scope(actor: User, assignment: Assignment) -> None:
    if actor.is_superuser:
        return
    if not user_has_permission(actor, "assignments.verify"):
        raise HTTPException(status_code=403, detail="Permission required: assignments.verify")
    if user_has_permission(actor, "assignments.manage_all"):
        return
    if actor.department_id != assignment.department_id:
        raise HTTPException(status_code=403, detail="You may verify assignments only for your department.")


def _assignment_activity(db, assignment, actor, action, previous_status, new_status, notes):
    repository.add_activity(db, AssignmentActivity(
        assignment_id=assignment.id,
        actor_user_id=actor.id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        notes=notes,
    ))


def _incident_activity(db, incident, actor, action, previous_status, new_status, notes):
    incident_repository.add_activity(db, IncidentActivity(
        incident_id=incident.id,
        actor_user_id=actor.id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        notes=notes,
    ))


def create_assignment(db: Session, actor: User, payload: AssignmentCreate) -> Assignment:
    incident = incident_repository.get_visible(db, actor, payload.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.status in {IncidentStatus.resolved, IncidentStatus.dismissed}:
        raise HTTPException(status_code=400, detail="A closed incident cannot receive a new assignment.")

    existing = repository.get_active_for_incident(db, incident.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"This incident already has an active assignment ({existing.assignment_number}).")

    department_id = payload.department_id if payload.department_id is not None else incident.department_id
    if department_id is None:
        raise HTTPException(status_code=400, detail="Select a department before creating the assignment.")

    _validate_department(db, department_id)
    _ensure_creation_scope(actor, department_id)
    assignee = _validate_assignee(db, payload.assigned_user_id, department_id)

    assignment = Assignment(
        assignment_number=generate_assignment_number(),
        incident_id=incident.id,
        department_id=department_id,
        assigned_user_id=assignee.id,
        assigned_by_id=actor.id,
        title=(payload.title or incident.title).strip(),
        instructions=payload.instructions.strip() if payload.instructions else incident.description,
        priority=payload.priority.value if payload.priority is not None else incident.priority.value,
        status=AssignmentStatus.pending,
        due_at=payload.due_at,
    )
    repository.create(db, assignment)

    previous_incident_status = incident.status
    incident.department_id = department_id
    incident.assigned_user_id = assignee.id
    incident.status = IncidentStatus.assigned

    _assignment_activity(db, assignment, actor, "assignment.created", None, AssignmentStatus.pending, payload.instructions or f"Assigned to {assignee.full_name}.")
    _incident_activity(db, incident, actor, "incident.assigned", previous_incident_status, IncidentStatus.assigned, f"{assignment.assignment_number} assigned to {assignee.full_name}.")

    db.flush()
    db.refresh(assignment)
    db.refresh(incident)

    alert_service.notify_users(
        db,
        recipients=[assignee],
        actor=actor,
        incident=incident,
        title=f"New assignment: {assignment.assignment_number}",
        message=f"You have been assigned {incident.incident_number}: {assignment.title}.",
        action_url=f"/assignments?assignment={assignment.id}",
        severity=alert_service.severity_from_incident(incident),
    )

    db.commit()
    db.refresh(assignment)
    return assignment


def create_from_incident_assignment(db, actor, incident, *, assigned_user_id, department_id, notes):
    return create_assignment(db, actor, AssignmentCreate(
        incident_id=incident.id,
        assigned_user_id=assigned_user_id,
        department_id=department_id,
        title=incident.title,
        instructions=notes or incident.description,
        priority=incident.priority,
    ))


def accept_assignment(db: Session, actor: User, assignment: Assignment) -> Assignment:
    if assignment.assigned_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assigned employee can accept this assignment.")
    if assignment.status != AssignmentStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending assignments can be accepted.")

    now = datetime.now(timezone.utc)
    previous = assignment.status
    assignment.status = AssignmentStatus.accepted
    assignment.accepted_at = now
    if assignment.incident.acknowledged_at is None:
        assignment.incident.acknowledged_at = now

    _assignment_activity(db, assignment, actor, "assignment.accepted", previous, assignment.status, "Assignment accepted by the assigned employee.")
    alert_service.notify_users(db, recipients=[assignment.assigned_by], actor=actor, incident=assignment.incident, title=f"Assignment accepted: {assignment.assignment_number}", message=f"{actor.full_name} accepted {assignment.title}.", action_url=f"/assignments?assignment={assignment.id}")

    db.commit()
    db.refresh(assignment)
    return assignment


def reject_assignment(db: Session, actor: User, assignment: Assignment, reason: str) -> Assignment:
    if assignment.assigned_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assigned employee can reject this assignment.")
    if assignment.status not in {AssignmentStatus.pending, AssignmentStatus.accepted}:
        raise HTTPException(status_code=400, detail="This assignment can no longer be rejected.")

    previous = assignment.status
    incident = assignment.incident
    previous_incident_status = incident.status

    assignment.status = AssignmentStatus.rejected
    assignment.rejection_reason = reason.strip()
    if incident.assigned_user_id == actor.id:
        incident.assigned_user_id = None
    if incident.status not in {IncidentStatus.resolved, IncidentStatus.dismissed}:
        incident.status = IncidentStatus.confirmed

    _assignment_activity(db, assignment, actor, "assignment.rejected", previous, assignment.status, reason.strip())
    _incident_activity(db, incident, actor, "assignment.rejected", previous_incident_status, incident.status, f"{assignment.assignment_number} rejected: {reason.strip()}")

    alert_service.notify_users(db, recipients=[assignment.assigned_by], actor=actor, incident=incident, title=f"Assignment rejected: {assignment.assignment_number}", message=f"{actor.full_name} rejected the assignment. Reason: {reason.strip()}", action_url=f"/assignments?assignment={assignment.id}", severity=alert_service.severity_from_incident(incident))

    db.commit()
    db.refresh(assignment)
    return assignment


def start_assignment(db: Session, actor: User, assignment: Assignment) -> Assignment:
    if assignment.assigned_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assigned employee can start this assignment.")
    if assignment.status != AssignmentStatus.accepted:
        raise HTTPException(status_code=400, detail="Accept the assignment before starting work.")

    previous = assignment.status
    incident = assignment.incident
    previous_incident_status = incident.status

    assignment.status = AssignmentStatus.in_progress
    assignment.started_at = datetime.now(timezone.utc)
    if incident.status not in {IncidentStatus.resolved, IncidentStatus.dismissed}:
        incident.status = IncidentStatus.in_progress

    _assignment_activity(db, assignment, actor, "assignment.started", previous, assignment.status, "Work started.")
    _incident_activity(db, incident, actor, "incident.status.in_progress", previous_incident_status, incident.status, f"Work started under {assignment.assignment_number}.")
    alert_service.notify_users(db, recipients=[assignment.assigned_by], actor=actor, incident=incident, title=f"Work started: {assignment.assignment_number}", message=f"{actor.full_name} started work on {assignment.title}.", action_url=f"/assignments?assignment={assignment.id}")

    db.commit()
    db.refresh(assignment)
    return assignment


def _verification_recipients(db: Session, assignment: Assignment) -> list[User]:
    users = list(db.scalars(select(User).where(
        User.is_active.is_(True),
        User.is_superuser.is_(False),
        User.department_id == assignment.department_id,
    )).unique().all())

    recipients = [u for u in users if user_has_permission(u, "assignments.verify")]
    recipients.append(assignment.assigned_by)

    seen, result = set(), []
    for user in recipients:
        if user.id not in seen:
            seen.add(user.id)
            result.append(user)
    return result


def submit_assignment(db: Session, actor: User, assignment: Assignment, payload: AssignmentSubmit) -> Assignment:
    if assignment.assigned_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assigned employee can submit this assignment.")
    if assignment.status != AssignmentStatus.in_progress:
        raise HTTPException(status_code=400, detail="Only in-progress assignments can be submitted.")

    evidence_items = []
    for evidence_id in list(dict.fromkeys(payload.evidence_ids)):
        evidence = repository.get_evidence(db, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} was not found.")
        if evidence.incident_id != assignment.incident_id:
            raise HTTPException(status_code=400, detail="Completion evidence must belong to the assignment incident.")
        evidence_items.append(evidence)

    previous = assignment.status
    assignment.status = AssignmentStatus.submitted
    assignment.submitted_at = datetime.now(timezone.utc)
    assignment.completion_notes = payload.completion_notes.strip()
    assignment.rejection_reason = None

    existing_ids = {e.id for e in repository.evidence_for_assignment(db, assignment.id)}
    for evidence in evidence_items:
        if evidence.id not in existing_ids:
            repository.add_evidence_link(db, AssignmentEvidenceLink(
                assignment_id=assignment.id,
                evidence_id=evidence.id,
                added_by_id=actor.id,
            ))

    _assignment_activity(db, assignment, actor, "assignment.submitted", previous, assignment.status, payload.completion_notes.strip())

    alert_service.notify_users(
        db,
        recipients=_verification_recipients(db, assignment),
        actor=actor,
        incident=assignment.incident,
        title=f"Assignment ready for verification: {assignment.assignment_number}",
        message=f"{actor.full_name} submitted completion evidence for {assignment.title}.",
        action_url=f"/assignments?assignment={assignment.id}",
        severity=alert_service.severity_from_incident(assignment.incident),
    )

    db.commit()
    db.refresh(assignment)
    return assignment


def verify_assignment(db: Session, actor: User, assignment: Assignment, *, approved: bool, notes: str) -> Assignment:
    _ensure_verification_scope(actor, assignment)
    if assignment.status != AssignmentStatus.submitted:
        raise HTTPException(status_code=400, detail="Only submitted assignments can be verified.")

    incident = assignment.incident
    previous = assignment.status
    previous_incident_status = incident.status
    cleaned_notes = notes.strip()

    if approved:
        assignment.status = AssignmentStatus.completed
        assignment.completed_at = datetime.now(timezone.utc)
        assignment.verification_notes = cleaned_notes
        incident.status = IncidentStatus.resolved
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolution_notes = f"{assignment.completion_notes}\n\nVerification: {cleaned_notes}"
        action = "assignment.completed"
        incident_action = "incident.status.resolved"
        title = f"Assignment completed: {assignment.assignment_number}"
        message = f"{assignment.assignment_number} was verified and completed."
        severity = alert_service.AlertSeverity.info
    else:
        assignment.status = AssignmentStatus.in_progress
        assignment.rejection_reason = cleaned_notes
        assignment.verification_notes = cleaned_notes
        incident.status = IncidentStatus.in_progress
        incident.resolved_at = None
        action = "assignment.verification_rejected"
        incident_action = "assignment.verification_rejected"
        title = f"Assignment returned: {assignment.assignment_number}"
        message = f"Completion for {assignment.assignment_number} was returned for further work."
        severity = alert_service.severity_from_incident(incident)

    _assignment_activity(db, assignment, actor, action, previous, assignment.status, cleaned_notes)
    _incident_activity(db, incident, actor, incident_action, previous_incident_status, incident.status, cleaned_notes)

    alert_service.notify_users(db, recipients=[assignment.assigned_user], actor=actor, incident=incident, title=title, message=message, action_url=f"/assignments?assignment={assignment.id}", severity=severity)

    db.commit()
    db.refresh(assignment)
    return assignment


def cancel_assignment(db: Session, actor: User, assignment: Assignment, reason: str) -> Assignment:
    _ensure_management_scope(actor, assignment)
    if assignment.status in TERMINAL_ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="This assignment is already closed.")

    previous = assignment.status
    incident = assignment.incident
    previous_incident_status = incident.status

    assignment.status = AssignmentStatus.cancelled
    assignment.cancelled_at = datetime.now(timezone.utc)
    assignment.cancellation_reason = reason.strip()

    if incident.assigned_user_id == assignment.assigned_user_id:
        incident.assigned_user_id = None
    if incident.status not in {IncidentStatus.resolved, IncidentStatus.dismissed}:
        incident.status = IncidentStatus.confirmed

    _assignment_activity(db, assignment, actor, "assignment.cancelled", previous, assignment.status, reason.strip())
    _incident_activity(db, incident, actor, "assignment.cancelled", previous_incident_status, incident.status, reason.strip())

    alert_service.notify_users(db, recipients=[assignment.assigned_user], actor=actor, incident=incident, title=f"Assignment cancelled: {assignment.assignment_number}", message=f"{assignment.title} was cancelled. Reason: {reason.strip()}", action_url=f"/assignments?assignment={assignment.id}")

    db.commit()
    db.refresh(assignment)
    return assignment


def assignment_to_read(db: Session, assignment: Assignment) -> AssignmentRead:
    data = AssignmentRead.model_validate(assignment)
    data.evidence = repository.evidence_for_assignment(db, assignment.id)
    return data


def to_list_response(db: Session, assignments: list[Assignment], total: int, page: int, page_size: int) -> AssignmentListResponse:
    return AssignmentListResponse(
        items=[assignment_to_read(db, item) for item in assignments],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def summary_for_actor(db: Session, actor: User) -> AssignmentSummary:
    return AssignmentSummary(**repository.counts_for_actor(db, actor))


def assignees_for_actor(db: Session, actor: User, department_id: int | None) -> list[User]:
    if actor.is_superuser or user_has_permission(actor, "assignments.manage_all"):
        return repository.active_assignees(db, department_id=department_id)

    if not (
        user_has_permission(actor, "assignments.create")
        or user_has_permission(actor, "incidents.assign")
    ):
        raise HTTPException(
            status_code=403,
            detail="Permission required: assignments.create or incidents.assign",
        )

    if actor.department_id is None:
        return []

    if department_id is not None and department_id != actor.department_id:
        raise HTTPException(status_code=403, detail="You may list assignees only from your department.")

    return repository.active_assignees(db, department_id=actor.department_id)


def backfill_existing_incident_assignments(db: Session) -> int:
    incidents = list(db.scalars(select(Incident).where(
        Incident.assigned_user_id.is_not(None),
        Incident.department_id.is_not(None),
    )).unique().all())

    created = 0
    for incident in incidents:
        existing = db.scalar(select(Assignment).where(Assignment.incident_id == incident.id))
        if existing is not None:
            continue

        if incident.status == IncidentStatus.resolved:
            assignment_status = AssignmentStatus.completed
        elif incident.status == IncidentStatus.dismissed:
            assignment_status = AssignmentStatus.cancelled
        elif incident.status == IncidentStatus.in_progress:
            assignment_status = AssignmentStatus.in_progress
        else:
            assignment_status = AssignmentStatus.pending

        assignment = Assignment(
            assignment_number=generate_assignment_number(),
            incident_id=incident.id,
            department_id=incident.department_id,
            assigned_user_id=incident.assigned_user_id,
            assigned_by_id=incident.created_by_id,
            title=incident.title,
            instructions="Imported from the incident assignment that existed before the formal Assignments module.",
            priority=incident.priority.value,
            status=assignment_status,
            accepted_at=incident.acknowledged_at,
            started_at=incident.acknowledged_at if assignment_status == AssignmentStatus.in_progress else None,
            completed_at=incident.resolved_at if assignment_status == AssignmentStatus.completed else None,
            cancelled_at=incident.updated_at if assignment_status == AssignmentStatus.cancelled else None,
            completion_notes=incident.resolution_notes,
        )
        db.add(assignment)
        db.flush()
        db.add(AssignmentActivity(
            assignment_id=assignment.id,
            actor_user_id=incident.created_by_id,
            action="assignment.backfilled",
            previous_status=None,
            new_status=assignment.status,
            notes="Created from an existing incident assignment.",
        ))
        created += 1

    return created
