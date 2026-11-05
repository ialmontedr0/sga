from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.locations import reports, schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/locations", tags=["Ubicaciones"])
reports_router = APIRouter(
    prefix="/locations/reports",
    tags=["Ubicaciones - Reportes"],
)


@router.get("/occupancy", response_model=schemas.OccupancySummaryOut)
async def get_occupancy(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    tray_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.OccupancySummaryOut:
    return await services.get_occupancy(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=tray_id,
    )


@router.get("/plan", response_model=schemas.LocationPlanOut)
async def get_location_plan(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    include_positions: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.LocationPlanOut:
    return await services.get_location_plan(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
        include_positions=include_positions,
    )


@router.get("/positions", response_model=Page[schemas.PositionOccupancyOut])
async def list_position_occupancy(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    tray_id: UUID | None = None,
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"] | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.PositionOccupancyOut]:
    return await services.list_position_occupancy(
        session,
        params=params,
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=tray_id,
        state=state,
        q=q,
    )


@router.get("/unlocated-boxes", response_model=Page[schemas.UnlocatedBoxOut])
async def list_unlocated_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    state: Literal["UNASSIGNED", "PENDING_CONFIRMATION"] | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.UnlocatedBoxOut]:
    return await services.list_unlocated_boxes(
        session,
        params=params,
        state=state,
        q=q,
    )


@router.get("/scan", response_model=schemas.ScanResponse)
async def scan_location(
    box_number: Annotated[str | None, Query(max_length=32)] = None,
    position_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.ScanResponse:
    return await services.scan(
        session,
        box_number=box_number,
        position_id=position_id,
    )


@reports_router.get("/occupancy", response_model=schemas.OccupancyReportOut)
async def get_occupancy_report(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.REPORTS_READ)),
) -> schemas.OccupancyReportOut:
    return await services.occupancy_report(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
    )


@reports_router.get("/occupancy.csv")
async def export_occupancy_csv(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.REPORTS_EXPORT)),
) -> Response:
    content = await reports.occupancy_csv(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="ocupacion.csv"',
        },
    )
