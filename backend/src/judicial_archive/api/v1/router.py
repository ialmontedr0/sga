from __future__ import annotations

from fastapi import APIRouter

from judicial_archive.api.v1 import health
from judicial_archive.modules.auth.routers import router as auth_router
from judicial_archive.modules.users.routers import router as users_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Salud"])
api_router.include_router(auth_router)
api_router.include_router(users_router)
