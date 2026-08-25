from datetime import datetime, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import user_has_permission
from app.modules.assignments.models import Assignment, AssignmentActivity, AssignmentEvidenceLink, AssignmentStatus
from app.modules.evidence.models import Evidence
from app.modules.users.models import User


ACTIVE_ASSIGNMENT_STATUSES = {
    AssignmentStatus.pending,
    AssignmentStatus.accepted,
    AssignmentStatus.in_progress,
    AssignmentStatus.submitted,
}


def visible_assignment_filter(actor: User):
    if actor.is_superuser or user_has_permission(actor, "assignments.view_all") or user_has_permission(actor, "assignments.manage_all"):
        return True

    conditions = [
        Assignment.assigned_user_id == actor.id,
        Assignment.assigned_by_id == actor.id,
    ]

    if actor.department_id is not None and (
        user_has_permission(actor, "assignments.view_department")
        or user_has_permission(actor, "assignments.manage_department")
        or user_has_permission(actor, "assignments.verify")
    ):
        conditions.append(Assignment.department_id == actor.department_id)

    return or_(*conditions)


def list_assignments(
    db: Session,
    actor: User,
    *,
    page: int,
    page_size: int,
    status_value: AssignmentStatus | None = None,
    department_id: int | None = None,
    assigned_user_id: int | None = None,
    incident_id: int | None = None,
    mine: bool = False,
    search: str | None = None,
) -> tuple[list[Assignment], int]:
    filters = [visible_assignment_filter(actor)]

    if status_value is not None:
        filters.append(Assignment.status == status_value)
    if department_id is not None:
        filters.append(Assignment.department_id == department_id)
    if assigned_user_id is not None:
        filters.append(Assignment.assigned_user_id == assigned_user_id)
    if incident_id is not None:
        filters.append(Assignment.incident_id == incident_id)
    if mine:
        filters.append(Assignment.assigned_user_id == actor.id)

    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(
            Assignment.assignment_number.ilike(pattern),
            Assignment.title.ilike(pattern),
            Assignment.instructions.ilike(pattern),
        ))

    total = int(db.scalar(select(func.count(Assignment.id)).where(*filters)) or 0)

    statement = (
        select(Assignment)
        .where(*filters)
        .order_by(Assignment.created_at.desc(), Assignment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).unique().all()), total


def get_visible(db: Session, actor: User, assignment_id: int) -> Assignment | None:
    return db.scalar(select(Assignment).where(
        Assignment.id == assignment_id,
        visible_assignment_filter(actor),
    ))


def get_active_for_incident(db: Session, incident_id: int) -> Assignment | None:
    return db.scalar(select(Assignment).where(
        Assignment.incident_id == incident_id,
        Assignment.status.in_(list(ACTIVE_ASSIGNMENT_STATUSES)),
    ))


def create(db: Session, assignment: Assignment) -> Assignment:
    db.add(assignment)
    db.flush()
    return assignment


def save(db: Session, assignment: Assignment) -> Assignment:
    db.add(assignment)
    db.flush()
    return assignment


def add_activity(db: Session, activity: AssignmentActivity) -> AssignmentActivity:
    db.add(activity)
    db.flush()
    return activity


def list_activities(db: Session, assignment_id: int) -> list[AssignmentActivity]:
    statement = (
        select(AssignmentActivity)
        .where(AssignmentActivity.assignment_id == assignment_id)
        .order_by(AssignmentActivity.created_at.asc(), AssignmentActivity.id.asc())
    )
    return list(db.scalars(statement).unique().all())


def get_evidence(db: Session, evidence_id: int) -> Evidence | None:
    return db.get(Evidence, evidence_id)


def add_evidence_link(db: Session, link: AssignmentEvidenceLink) -> AssignmentEvidenceLink:
    db.add(link)
    db.flush()
    return link


def evidence_for_assignment(db: Session, assignment_id: int) -> list[Evidence]:
    statement = (
        select(Evidence)
        .join(AssignmentEvidenceLink, AssignmentEvidenceLink.evidence_id == Evidence.id)
        .where(AssignmentEvidenceLink.assignment_id == assignment_id)
        .order_by(Evidence.created_at.asc())
    )
    return list(db.scalars(statement).unique().all())


def active_assignees(db: Session, *, department_id: int | None = None) -> list[User]:
    filters = [User.is_active.is_(True), User.is_superuser.is_(False)]
    if department_id is not None:
        filters.append(User.department_id == department_id)

    return list(db.scalars(
        select(User).where(*filters).order_by(User.full_name.asc())
    ).unique().all())


def counts_for_actor(db: Session, actor: User) -> dict[str, int]:
    visibility = visible_assignment_filter(actor)

    def count(*extra_filters) -> int:
        return int(db.scalar(
            select(func.count(Assignment.id)).where(visibility, *extra_filters)
        ) or 0)

    now = datetime.now(timezone.utc)
    open_statuses = [
        AssignmentStatus.pending,
        AssignmentStatus.accepted,
        AssignmentStatus.in_progress,
        AssignmentStatus.submitted,
    ]

    return {
        "total_visible": count(),
        "my_open": count(Assignment.assigned_user_id == actor.id, Assignment.status.in_(open_statuses)),
        "pending_acceptance": count(Assignment.assigned_user_id == actor.id, Assignment.status == AssignmentStatus.pending),
        "in_progress": count(Assignment.status == AssignmentStatus.in_progress),
        "awaiting_verification": count(Assignment.status == AssignmentStatus.submitted),
        "overdue": count(Assignment.due_at.is_not(None), Assignment.due_at < now, Assignment.status.in_(open_statuses)),
        "completed": count(Assignment.status == AssignmentStatus.completed),
    }
