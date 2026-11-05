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


@shelves_router.get("", response_model=Page[schemas.ShelfOut])
async def list_shelves(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    shelf_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.ShelfOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_SHELF_SORT)
    return await services.list_shelves(
        session,
        params=params,
        area_id=area_id,
        q=q,
        status=shelf_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@shelves_router.post(
    "",
    response_model=schemas.ShelfOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_shelf(
    request: Request,
    body: schemas.ShelfCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.create_shelf(request, session, current_user, body)


@shelves_router.get("/{shelf_id}", response_model=schemas.ShelfOut)
async def get_shelf(
    shelf_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.ShelfOut:
    return await services.get_shelf(session, shelf_id)


@shelves_router.patch("/{shelf_id}", response_model=schemas.ShelfOut)
async def update_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.update_shelf(request, session, current_user, shelf_id, body)


@shelves_router.post("/{shelf_id}/activate", response_model=schemas.ShelfOut)
async def activate_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.set_shelf_status(
        request, session, current_user, shelf_id, "ACTIVE", body.reason
    )


@shelves_router.post("/{shelf_id}/deactivate", response_model=schemas.ShelfOut)
async def deactivate_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.set_shelf_status(
        request, session, current_user, shelf_id, "INACTIVE", body.reason
    )


@shelves_router.post(
    "/{shelf_id}/capacity/preview",
    response_model=schemas.CapacityPlanOut,
)
async def preview_shelf_capacity(
    shelf_id: UUID,
    body: schemas.CapacityTarget,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.CapacityPlanOut:
    return await services.preview_capacity(session, shelf_id, body)


@shelves_router.post(
    "/{shelf_id}/capacity/apply",
    response_model=schemas.CapacityApplyOut,
)
async def apply_shelf_capacity(
    request: Request,
    shelf_id: UUID,
    body: schemas.CapacityApplyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CapacityApplyOut:
    return await services.apply_capacity(request, session, current_user, shelf_id, body)


@trays_router.get("", response_model=Page[schemas.TrayOut])
async def list_trays(
    params: Annotated[PageParams, Depends(pagination_params)],
    shelf_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    tray_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.TrayOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_TRAY_SORT)
    return await services.list_trays(
        session,
        params=params,
        shelf_id=shelf_id,
        q=q,
        status=tray_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@trays_router.post(
    "",
    response_model=schemas.TrayOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_tray(
    request: Request,
    body: schemas.TrayCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.create_tray(request, session, current_user, body)


@trays_router.get("/{tray_id}", response_model=schemas.TrayOut)
async def get_tray(
    tray_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.TrayOut:
    return await services.get_tray(session, tray_id)


@trays_router.patch("/{tray_id}", response_model=schemas.TrayOut)
async def update_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.update_tray(request, session, current_user, tray_id, body)


@trays_router.post("/{tray_id}/activate", response_model=schemas.TrayOut)
async def activate_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.set_tray_status(
        request, session, current_user, tray_id, "ACTIVE", body.reason
    )


@trays_router.post("/{tray_id}/deactivate", response_model=schemas.TrayOut)
async def deactivate_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.set_tray_status(
        request, session, current_user, tray_id, "INACTIVE", body.reason
    )


@positions_router.get("", response_model=Page[schemas.PositionOut])
async def list_positions(
    params: Annotated[PageParams, Depends(pagination_params)],
    tray_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    position_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PositionOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_POSITION_SORT)
    return await services.list_positions(
        session,
        params=params,
        tray_id=tray_id,
        q=q,
        status=position_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@positions_router.post(
    "",
    response_model=schemas.PositionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_position(
    request: Request,
    body: schemas.PositionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.create_position(request, session, current_user, body)


@positions_router.get("/{position_id}", response_model=schemas.PositionOut)
async def get_position(
    position_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.PositionOut:
    return await services.get_position(session, position_id)


@positions_router.patch("/{position_id}", response_model=schemas.PositionOut)
async def update_position(
    request: Request,
    position_id: UUID,
    body: schemas.PositionUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.update_position(request, session, current_user, position_id, body)


@positions_router.post("/{position_id}/retire", response_model=schemas.PositionOut)
async def retire_position(
    request: Request,
    position_id: UUID,
    body: schemas.PositionRetireRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.retire_position(request, session, current_user, position_id, body)


@positions_router.post("/{position_id}/activate", response_model=schemas.PositionOut)
async def activate_position(
    request: Request,
    position_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.activate_position(request, session, current_user, position_id)
