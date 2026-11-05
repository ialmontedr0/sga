from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.locations import blocks, schemas
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/position-blocks", tags=["Ubicaciones - Bloqueos"])


@router.get("", response_model=Page[schemas.PositionBlockOut])
async def list_position_blocks(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    active: Annotated[bool | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PositionBlockOut]:
    return await blocks.list_blocks(
        session,
        params=params,
        area_id=area_id,
        shelf_id=shelf_id,
        active=active,
    )


@router.post(
    "",
    response_model=schemas.PositionBlockOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_position_block(
    request: Request,
    body: schemas.PositionBlockCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionBlockOut:
    return await blocks.create_block(request, session, current_user, body)


@router.post("/{block_id}/cancel", response_model=schemas.PositionBlockOut)
async def cancel_position_block(
    request: Request,
    block_id: UUID,
    body: schemas.PositionBlockCancel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionBlockOut:
    return await blocks.cancel_block(
        request,
        session,
        current_user,
        block_id,
        body,
    )
