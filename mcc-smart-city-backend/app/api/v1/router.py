from fastapi import APIRouter
from app.modules.authentication.router import router as authentication_router
from app.modules.departments.router import router as departments_router
from app.modules.navigation.router import router as navigation_router
from app.modules.permissions.router import router as permissions_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router
api_router=APIRouter()
for router in [authentication_router,departments_router,roles_router,permissions_router,users_router,navigation_router]: api_router.include_router(router)
