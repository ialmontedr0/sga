from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.enums import CourtStatus
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)
from judicial_archive.modules.courts import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/courts", tags=["Catalogos - Tribunales"])
_ALLOWED_SORT = frozenset({"code_normalized", "name", "status", "created_at", "updated_at"})


@router.get("", response_model=Page[schemas.CourtOut])
async def list_courts(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_status: Annotated[CourtStatus | None, Query(alias="status")] = None,
    court_type: Annotated[str | None, Query(max_length=80)] = None,
    effective_on: date | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.CourtOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_ALLOWED_SORT)
    return await services.list_courts(
        session,
        params=params,
        q=q,
        status=court_status.value if court_status else None,
        court_type=court_type,
        effective_on=effective_on,
        sort_by=sort.sort_by or "name",
        order=sort.order,
    )


@router.get("/{court_id}", response_model=schemas.CourtOut)
async def get_court(
    court_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> schemas.CourtOut:
    return await services.get_court(session, court_id)


@router.post("", response_model=schemas.CourtOut, status_code=status.HTTP_201_CREATED)
async def create_court(
    request: Request,
    body: schemas.CourtCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.create_court(request, session, current_user, body)


@router.patch("/{court_id}", response_model=schemas.CourtOut)
async def update_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.update_court(request, session, current_user, court_id, body)


@router.post("/{court_id}/activate", response_model=schemas.CourtOut)
async def activate_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.set_court_status(
        request, session, current_user, court_id, CourtStatus.ACTIVE, body.reason
    )


@router.post("/{court_id}/deactivate", response_model=schemas.CourtOut)
async def deactivate_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.set_court_status(
        request, session, current_user, court_id, CourtStatus.INACTIVE, body.reason
    )
