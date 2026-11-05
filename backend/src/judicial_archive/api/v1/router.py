from __future__ import annotations

from fastapi import APIRouter

from judicial_archive.api.v1 import health
from judicial_archive.modules.auth.routers import router as auth_router
from judicial_archive.modules.courts.routers import router as courts_router
from judicial_archive.modules.identifier_profiles.routers import (
    router as identifier_profiles_router,
)
from judicial_archive.modules.locations.blocks_router import router as position_blocks_router
from judicial_archive.modules.locations.occupancy_router import (
    reports_router as location_reports_router,
    router as locations_router,
)
from judicial_archive.modules.locations.routers import (
    areas_router,
    box_types_router,
    positions_router,
    shelves_router,
    trays_router,
)
from judicial_archive.modules.movements.routers import box_locations_router, movements_router
from judicial_archive.modules.numbering.routers import router as numbering_router
from judicial_archive.modules.party_roles.routers import router as party_roles_router
from judicial_archive.modules.resolution_types.routers import router as resolution_types_router
from judicial_archive.modules.roles.routers import permissions_router, router as roles_router
from judicial_archive.modules.settings.routers import router as settings_router
from judicial_archive.modules.users.routers import router as users_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Salud"])
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(courts_router)
api_router.include_router(identifier_profiles_router)
api_router.include_router(areas_router)
api_router.include_router(box_types_router)
api_router.include_router(positions_router)
api_router.include_router(shelves_router)
api_router.include_router(trays_router)
api_router.include_router(numbering_router)
api_router.include_router(party_roles_router)
api_router.include_router(resolution_types_router)
api_router.include_router(settings_router)
api_router.include_router(locations_router)
api_router.include_router(location_reports_router)
api_router.include_router(position_blocks_router)
api_router.include_router(box_locations_router)
api_router.include_router(movements_router)
