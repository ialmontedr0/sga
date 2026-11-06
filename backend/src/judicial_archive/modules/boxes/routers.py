from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.boxes import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/boxes", tags=["Cajas"])


@router.get("", response_model=Page[schemas.BoxOut])
async def list_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_id: UUID | None = None,
    year: int | None = None,
    box_type: str | None = None,
    lifecycle_status: str | None = None,
    custody_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> Page[schemas.BoxOut]:
    return await services.list_boxes(
        session,
        params=params,
        q=q,
        court_id=court_id,
        year=year,
        box_type=box_type,
        lifecycle_status=lifecycle_status,
        custody_status=custody_status,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{box_id}", response_model=schemas.BoxOut)
async def get_box(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxOut:
    return await services.get_box(session, box_id)


@router.get("/{box_id}/content-summary", response_model=schemas.BoxContentSummaryOut)
async def get_box_content_summary(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxContentSummaryOut:
    return await services.get_box_content_summary(session, box_id)


@router.get("/{box_id}/number-history", response_model=Page[schemas.BoxNumberHistoryOut])
async def list_box_number_history(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> Page[schemas.BoxNumberHistoryOut]:
    return await services.list_box_number_history(session, box_id=box_id, params=params)


@router.post("", response_model=schemas.BoxOut)
async def create_box(
    request: Request,
    body: schemas.BoxCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_CREATE)),
) -> schemas.BoxOut:
    return await services.create_box(request, session, current_user, body)


@router.post("/with-content", response_model=schemas.BoxWithContentOut)
async def create_box_with_content(
    request: Request,
    body: schemas.BoxWithContentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_CREATE)),
) -> schemas.BoxWithContentOut:
    return await services.create_box_with_content(request, session, current_user, body)


@router.patch("/{box_id}", response_model=schemas.BoxOut)
async def update_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.update_box(request, session, current_user, box_id, body)


@router.post("/{box_id}/number-corrections", response_model=schemas.BoxOut)
async def correct_box_number(
    request: Request,
    box_id: UUID,
    body: schemas.BoxNumberCorrection,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.correct_box_number(request, session, current_user, box_id, body)


@router.post("/{box_id}/archive", response_model=schemas.BoxOut)
async def archive_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.set_box_lifecycle(
        request,
        session,
        current_user,
        box_id,
        target="ARCHIVED",
        body=body,
    )


@router.post("/{box_id}/void", response_model=schemas.BoxOut)
async def void_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.set_box_lifecycle(
        request,
        session,
        current_user,
        box_id,
        target="VOIDED",
        body=body,
    )
