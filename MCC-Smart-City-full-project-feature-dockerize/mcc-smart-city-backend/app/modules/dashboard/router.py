from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.core.deps import (
    get_db,
    require_permission,
)
from app.modules.dashboard import service
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
        db: Session = Depends(get_db),
        actor: User = Depends(
            require_permission(
                "incidents.view"
            )
        ),
) -> DashboardSummaryResponse:
    return service.get_summary(
        db,
        actor,
    )