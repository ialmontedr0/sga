from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.resolution_types import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/resolution-types", tags=["resolution-types"])


@router.get("", response_model=Page[schemas.ResolutionTypeOut])
async def list_resolution_types(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.ResolutionTypeOut]:
    return await services.list_resolution_types(
        session, params=params, q=q, status=status_filter, sort_by=sort_by, order=order
    )


@router.get("/{item_id}", response_model=schemas.ResolutionTypeOut)
async def get_resolution_type(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.ResolutionTypeOut:
    return await services.get_resolution_type(session, item_id)


@router.post("", response_model=schemas.ResolutionTypeOut, status_code=status.HTTP_201_CREATED)
async def create_resolution_type(
    request: Request,
    body: schemas.ResolutionTypeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.create_resolution_type(request, session, current_user, body)


@router.patch("/{item_id}", response_model=schemas.ResolutionTypeOut)
async def update_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.update_resolution_type(request, session, current_user, item_id, body)


@router.post("/{item_id}/activate", response_model=schemas.ResolutionTypeOut)
async def activate_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.set_resolution_type_status(
        request, session, current_user, item_id, active=True, reason=body.reason
    )


@router.post("/{item_id}/deactivate", response_model=schemas.ResolutionTypeOut)
async def deactivate_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.set_resolution_type_status(
        request, session, current_user, item_id, active=False, reason=body.reason
    )
