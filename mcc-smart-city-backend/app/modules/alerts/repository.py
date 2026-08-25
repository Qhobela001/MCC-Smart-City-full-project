from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.users.models import User


def list_for_user(
    db: Session,
    user_id: int,
    *,
    limit: int,
    offset: int,
    unread_only: bool,
    include_archived: bool,
) -> tuple[list[Alert], int]:
    filters = [
        Alert.recipient_user_id == user_id,
    ]

    if unread_only:
        filters.append(Alert.is_read.is_(False))

    if not include_archived:
        filters.append(Alert.is_archived.is_(False))

    total = int(
        db.scalar(
            select(func.count(Alert.id)).where(*filters)
        )
        or 0
    )

    statement = (
        select(Alert)
        .where(*filters)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset(offset)
        .limit(limit)
    )

    items = list(
        db.scalars(statement).unique().all()
    )
    return items, total


def unread_count(
    db: Session,
    user_id: int,
) -> int:
    return int(
        db.scalar(
            select(func.count(Alert.id)).where(
                Alert.recipient_user_id == user_id,
                Alert.is_read.is_(False),
                Alert.is_archived.is_(False),
            )
        )
        or 0
    )


def get_for_user(
    db: Session,
    alert_id: int,
    user_id: int,
) -> Alert | None:
    return db.scalar(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.recipient_user_id == user_id,
        )
    )


def create(
    db: Session,
    alert: Alert,
) -> Alert:
    db.add(alert)
    db.flush()
    return alert


def mark_all_read(
    db: Session,
    user_id: int,
) -> list[Alert]:
    alerts = list(
        db.scalars(
            select(Alert).where(
                Alert.recipient_user_id == user_id,
                Alert.is_read.is_(False),
                Alert.is_archived.is_(False),
            )
        ).all()
    )

    return alerts


def active_superadmins(
    db: Session,
) -> list[User]:
    statement = select(User).where(
        User.is_superuser.is_(True),
        User.is_active.is_(True),
    )
    return list(
        db.scalars(statement).unique().all()
    )


def active_department_users(
    db: Session,
    department_id: int,
) -> list[User]:
    statement = select(User).where(
        User.department_id == department_id,
        User.is_active.is_(True),
        User.is_superuser.is_(False),
    )
    return list(
        db.scalars(statement).unique().all()
    )
