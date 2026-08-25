from fastapi import APIRouter

from app.modules.alerts.router import router as alerts_router
from app.modules.analytics.router import router as analytics_router
from app.modules.assignments.router import router as assignments_router
from app.modules.authentication.router import router as authentication_router
from app.modules.cameras.router import router as cameras_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.departments.router import router as departments_router
from app.modules.devices.router import router as devices_router
from app.modules.evidence.router import router as evidence_router
from app.modules.gis.router import router as gis_router
from app.modules.incidents.router import router as incidents_router
from app.modules.live_streams.router import router as live_streams_router
from app.modules.navigation.router import router as navigation_router
from app.modules.permissions.router import router as permissions_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router
from app.modules.ai_detection.router import router as ai_detection_router
from app.modules.ai_detection.router import router as ai_detections_router


api_router = APIRouter()


for router in [
    analytics_router,
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
    dashboard_router,
    gis_router,
    cameras_router,
    devices_router,
    live_streams_router,
    ai_detection_router,
    ai_detections_router
]:
    api_router.include_router(router)