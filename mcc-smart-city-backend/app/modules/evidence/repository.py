from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.evidence.models import Evidence


def list_for_incident(
    db: Session,
    incident_id: int,
) -> list[Evidence]:
    statement = (
        select(Evidence)
        .where(Evidence.incident_id == incident_id)
        .order_by(
            Evidence.created_at.desc(),
            Evidence.id.desc(),
        )
    )
    return list(
        db.scalars(statement).unique().all()
    )


def get(
    db: Session,
    evidence_id: int,
) -> Evidence | None:
    return db.get(Evidence, evidence_id)


def create(
    db: Session,
    evidence: Evidence,
) -> Evidence:
    db.add(evidence)
    db.flush()
    return evidence


def save(
    db: Session,
    evidence: Evidence,
) -> Evidence:
    db.add(evidence)
    db.flush()
    return evidence


def delete(
    db: Session,
    evidence: Evidence,
) -> None:
    db.delete(evidence)
    db.flush()
