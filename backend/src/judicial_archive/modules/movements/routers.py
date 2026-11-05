from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.boxes.schemas import BoxLocationHistoryOut
from judicial_archive.modules.movements import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

box_locations_router = APIRouter(
    prefix="/locations/boxes",
    tags=["Ubicaciones - Cajas"],
)
movements_router = APIRouter(prefix="/movements", tags=["Movimientos"])


@box_locations_router.get("/{box_id}", response_model=schemas.BoxLocationDetailOut)
async def get_box_location(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxLocationDetailOut:
    return await services.get_box_location(session, box_id)


@box_locations_router.get(
    "/{box_id}/history",
    response_model=Page[BoxLocationHistoryOut],
)
async def list_box_location_history(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    source: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[BoxLocationHistoryOut]:
    return await services.list_box_history(
        session,
        params=params,
        box_id=box_id,
        from_date=from_date,
        to_date=to_date,
        source=source,
    )


@box_locations_router.post(
    "/{box_id}/assign",
    response_model=schemas.LocationMutationOut,
)
async def assign_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.AssignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.assign_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/unassign",
    response_model=schemas.LocationMutationOut,
)
async def unassign_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.UnassignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.unassign_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/transfer",
    response_model=schemas.LocationMutationOut,
)
async def transfer_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.TransferRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.transfer_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/confirm",
    response_model=schemas.LocationMutationOut,
)
async def confirm_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.ConfirmRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.confirm_location(request, session, current_user, box_id, body)


@movements_router.get("", response_model=Page[schemas.MovementOut])
async def list_movements(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID | None = None,
    movement_type: str | None = None,
    movement_status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.MovementOut]:
    return await services.list_movements(
        session,
        params=params,
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_date=from_date,
        to_date=to_date,
    )


@movements_router.get("/{movement_id}", response_model=schemas.MovementOut)
async def get_movement(
    movement_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.MovementOut:
    return await services.get_movement(session, movement_id)


@movements_router.post(
    "/{movement_id}/complete",
    response_model=schemas.LocationMutationOut,
)
async def complete_movement(
    request: Request,
    movement_id: UUID,
    body: schemas.CompleteMovementRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.complete_movement(request, session, current_user, movement_id, body)


@movements_router.post(
    "/{movement_id}/cancel",
    response_model=schemas.LocationMutationOut,
)
async def cancel_movement(
    request: Request,
    movement_id: UUID,
    body: schemas.CancelMovementRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.cancel_movement(request, session, current_user, movement_id, body)
