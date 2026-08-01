from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


def list_all(db: Session) -> list[User]:
    statement = select(User).order_by(User.full_name)
    return list(db.scalars(statement).unique().all())


def list_all_non_superadmins(db: Session) -> list[User]:
    statement = (
        select(User)
        .where(User.is_superuser.is_(False))
        .order_by(User.full_name)
    )
    return list(db.scalars(statement).unique().all())


def list_visible_to(db: Session, actor: User) -> list[User]:
    if actor.is_superuser:
        return list_all(db)

    return list_all_non_superadmins(db)


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_visible_to(
    db: Session,
    actor: User,
    user_id: int,
) -> User | None:
    user = get(db, user_id)

    if user is None:
        return None

    if actor.is_superuser:
        return user

    if user.is_superuser:
        return None

    return user


def create(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
