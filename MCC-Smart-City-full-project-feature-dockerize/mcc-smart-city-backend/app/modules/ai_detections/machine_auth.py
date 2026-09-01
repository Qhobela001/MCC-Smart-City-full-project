import os
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.users.models import User, UserStatus


AI_WORKER_KEY_HEADER = "X-AI-Worker-Key"


def require_ai_worker(
    x_ai_worker_key: str = Header(
        default="",
        alias=AI_WORKER_KEY_HEADER,
    ),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate the internal AI worker and resolve its audit actor.

    The worker receives a separate machine credential; it never stores or
    reuses an operator JWT. Incidents and activities still require a real,
    active database user for their existing non-null audit foreign keys.
    """

    expected_key = os.getenv("AI_WORKER_SHARED_KEY", "").strip()

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI worker authentication is not configured.",
        )

    if not x_ai_worker_key or not secrets.compare_digest(
        x_ai_worker_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AI worker authentication failed.",
        )

    actor_email = os.getenv(
        "AI_INGEST_ACTOR_EMAIL",
        os.getenv("SUPERADMIN_EMAIL", "admin@mcc.org.ls"),
    ).strip().lower()

    actor = (
        db.query(User)
        .filter(func.lower(User.email) == actor_email)
        .first()
    )

    if (
        actor is None
        or not actor.is_active
        or actor.status != UserStatus.active
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The configured AI ingestion audit actor is unavailable "
                "or inactive."
            ),
        )

    return actor
