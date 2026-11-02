from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.enums import BoxType
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)
from judicial_archive.modules.locations import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

areas_router = APIRouter(prefix="/areas", tags=["Catalogos - Areas"])
shelves_router = APIRouter(prefix="/shelves", tags=["Catalogos - Anaqueles"])
trays_router = APIRouter(prefix="/trays", tags=["Catalogos - Bandejas"])
positions_router = APIRouter(prefix="/positions", tags=["Catalogos - Posiciones"])
box_types_router = APIRouter(tags=["Catalogos - Tipos de caja"])

_AREA_SORT = frozenset({"code", "name", "status", "created_at", "updated_at"})
_SHELF_SORT = frozenset(
    {"code", "name", "status", "capacity_positions", "created_at", "updated_at"}
)
_TRAY_SORT = frozenset({"code", "status", "position_count", "created_at", "updated_at"})
_POSITION_SORT = frozenset({"code", "label", "status", "created_at", "updated_at"})


@areas_router.get("", response_model=Page[schemas.AreaOut])
async def list_areas(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    area_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.AreaOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_AREA_SORT)
    return await services.list_areas(
        session,
        params=params,
        q=q,
        status=area_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@areas_router.post("", response_model=schemas.AreaOut, status_code=status.HTTP_201_CREATED)
async def create_area(
    request: Request,
    body: schemas.AreaCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.create_area(request, session, current_user, body)


@areas_router.patch("/{area_id}", response_model=schemas.AreaOut)
async def update_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.update_area(request, session, current_user, area_id, body)


@areas_router.post("/{area_id}/activate", response_model=schemas.AreaOut)
async def activate_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.set_area_status(
        request, session, current_user, area_id, "ACTIVE", body.reason
    )


@areas_router.post("/{area_id}/deactivate", response_model=schemas.AreaOut)
async def deactivate_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.set_area_status(
        request, session, current_user, area_id, "INACTIVE", body.reason
    )


@areas_router.get("/{area_id}", response_model=schemas.AreaOut)
async def get_area(
    area_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.AreaOut:
    return await services.get_area(session, area_id)


@box_types_router.get("/box-types", response_model=list[schemas.BoxTypeOut])
async def list_box_types(
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> list[schemas.BoxTypeOut]:
    return [
        schemas.BoxTypeOut(value=BoxType.EXPEDIENTES.value, label="Expedientes"),
        schemas.BoxTypeOut(
            value=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
            label="Documentos administrativos",
        ),
    ]
