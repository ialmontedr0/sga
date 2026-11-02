from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, pagination_params
from judicial_archive.modules.identifier_profiles import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/identifier-profiles", tags=["identifier-profiles"])


@router.get("", response_model=Page[schemas.IdentifierProfileOut])
async def list_identifier_profiles(
    params: Annotated[PageParams, Depends(pagination_params)],
    court_id: Annotated[UUID | None, Query()] = None,
    identifier_kind: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.IdentifierProfileOut]:
    return await services.list_identifier_profiles(
        session,
        params=params,
        court_id=court_id,
        identifier_kind=identifier_kind,
        is_active=is_active,
    )


@router.get("/{profile_id}", response_model=schemas.IdentifierProfileOut)
async def get_identifier_profile(
    profile_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.IdentifierProfileOut:
    return await services.get_identifier_profile(session, profile_id)


@router.post("", response_model=schemas.IdentifierProfileOut, status_code=status.HTTP_201_CREATED)
async def create_identifier_profile(
    request: Request,
    body: schemas.IdentifierProfileCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.create_identifier_profile(request, session, current_user, body)


@router.patch("/{profile_id}", response_model=schemas.IdentifierProfileOut)
async def update_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.update_identifier_profile(
        request, session, current_user, profile_id, body
    )


@router.post("/{profile_id}/replace", response_model=schemas.IdentifierProfileOut)
async def replace_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileReplace,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.replace_identifier_profile(
        request, session, current_user, profile_id, body
    )


@router.post("/{profile_id}/activate", response_model=schemas.IdentifierProfileOut)
async def activate_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.set_identifier_profile_status(
        request,
        session,
        current_user,
        profile_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{profile_id}/deactivate", response_model=schemas.IdentifierProfileOut)
async def deactivate_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.set_identifier_profile_status(
        request,
        session,
        current_user,
        profile_id,
        active=False,
        reason=body.reason,
    )
