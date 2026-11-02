from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.party_roles import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/party-roles", tags=["party-roles"])


@router.get("", response_model=Page[schemas.PartyRoleOut])
async def list_party_roles(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PartyRoleOut]:
    return await services.list_party_roles(
        session,
        params=params,
        q=q,
        status=status_filter,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{item_id}", response_model=schemas.PartyRoleOut)
async def get_party_role(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.PartyRoleOut:
    return await services.get_party_role(session, item_id)


@router.post("", response_model=schemas.PartyRoleOut, status_code=status.HTTP_201_CREATED)
async def create_party_role(
    request: Request,
    body: schemas.PartyRoleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.create_party_role(request, session, current_user, body)


@router.patch("/{item_id}", response_model=schemas.PartyRoleOut)
async def update_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.update_party_role(request, session, current_user, item_id, body)


@router.post("/{item_id}/activate", response_model=schemas.PartyRoleOut)
async def activate_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.set_party_role_status(
        request,
        session,
        current_user,
        item_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{item_id}/deactivate", response_model=schemas.PartyRoleOut)
async def deactivate_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.set_party_role_status(
        request,
        session,
        current_user,
        item_id,
        active=False,
        reason=body.reason,
    )
