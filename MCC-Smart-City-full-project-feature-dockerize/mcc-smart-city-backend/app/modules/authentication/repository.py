from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.users.models import User


def find_by_identifier(
    db: Session,
    identifier: str,
) -> User | None:
    return db.scalar(
        select(User).where(
            or_(
                User.email == identifier.lower(),
                User.employee_number == identifier,
                User.phone_number == identifier,
            )
        )
    )


def find_by_email(
    db: Session,
    email: str,
) -> User | None:
    return db.scalar(
        select(User).where(
            User.email == email.strip().lower()
        )
    )


def find_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    return db.scalar(
        select(User).where(
            User.id == user_id
        )
    )
