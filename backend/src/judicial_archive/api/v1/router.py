from __future__ import annotations

from fastapi import APIRouter

from judicial_archive.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Salud"])
