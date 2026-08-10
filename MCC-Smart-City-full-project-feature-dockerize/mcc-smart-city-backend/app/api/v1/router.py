from fastapi import APIRouter

from app.modules.alerts.router import router as alerts_router
from app.modules.assignments.router import router as assignments_router
from app.modules.authentication.router import (
    router as authentication_router,
)
from app.modules.departments.router import (
    router as departments_router,
)
from app.modules.evidence.router import (
    router as evidence_router,
)
from app.modules.incidents.router import (
    router as incidents_router,
)
from app.modules.navigation.router import (
    router as navigation_router,
)
from app.modules.permissions.router import (
    router as permissions_router,
)
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router


api_router = APIRouter()

for router in [
    authentication_router,
    departments_router,
    roles_router,
    permissions_router,
    users_router,
    navigation_router,
    incidents_router,
    evidence_router,
    alerts_router,
    assignments_router,
]:
    api_router.include_router(router)
