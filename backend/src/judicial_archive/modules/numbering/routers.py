from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.numbering import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/numbering-policies", tags=["numbering-policies"])


@router.get("", response_model=Page[schemas.NumberingPolicyOut])
async def list_numbering_policies(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    scope: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    court_id: Annotated[UUID | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.NumberingPolicyOut]:
    return await services.list_numbering_policies(
        session,
        params=params,
        q=q,
        scope=scope,
        is_active=is_active,
        court_id=court_id,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{policy_id}", response_model=schemas.NumberingPolicyOut)
async def get_numbering_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.NumberingPolicyOut:
    return await services.get_numbering_policy(session, policy_id)


@router.get("/{policy_id}/preview", response_model=schemas.NumberingPreviewOut)
async def preview_numbering_policy(
    policy_id: UUID,
    value: Annotated[int, Query(ge=1)] = 1,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.NumberingPreviewOut:
    return await services.preview_numbering_policy(session, policy_id, value)


@router.post("", response_model=schemas.NumberingPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_numbering_policy(
    request: Request,
    body: schemas.NumberingPolicyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.create_numbering_policy(request, session, current_user, body)


@router.patch("/{policy_id}", response_model=schemas.NumberingPolicyOut)
async def update_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.update_numbering_policy(request, session, current_user, policy_id, body)


@router.post("/{policy_id}/activate", response_model=schemas.NumberingPolicyOut)
async def activate_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.set_numbering_policy_status(
        request,
        session,
        current_user,
        policy_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{policy_id}/deactivate", response_model=schemas.NumberingPolicyOut)
async def deactivate_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.set_numbering_policy_status(
        request,
        session,
        current_user,
        policy_id,
        active=False,
        reason=body.reason,
    )
