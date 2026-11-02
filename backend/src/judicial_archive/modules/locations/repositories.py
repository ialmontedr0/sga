from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray


class LocationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_area(self, area_id: UUID) -> Area | None:
        return await self.session.get(Area, area_id)

    async def get_shelf(self, shelf_id: UUID) -> Shelf | None:
        return await self.session.get(Shelf, shelf_id)

    async def get_tray(self, tray_id: UUID) -> Tray | None:
        return await self.session.get(Tray, tray_id)

    async def get_position(self, position_id: UUID) -> Position | None:
        return await self.session.get(Position, position_id)

    async def list_areas(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Area], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(Area.code.ilike(pattern, escape="\\"), Area.name.ilike(pattern, escape="\\"))
            )
        if status:
            conditions.append(Area.status == status)
        base = select(Area).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(Area, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Area.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_shelves(
        self,
        *,
        area_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Shelf], int]:
        conditions = []
        if area_id:
            conditions.append(Shelf.area_id == area_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(Shelf.code.ilike(pattern, escape="\\"), Shelf.name.ilike(pattern, escape="\\"))
            )
        if status:
            conditions.append(Shelf.status == status)
        base = select(Shelf).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(Shelf, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Shelf.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_trays(
        self,
        *,
        shelf_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Tray], int]:
        conditions = []
        if shelf_id:
            conditions.append(Tray.shelf_id == shelf_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Tray.code.ilike(pattern, escape="\\"),
                    Tray.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Tray.status == status)
        base = select(Tray).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(Tray, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Tray.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_positions(
        self,
        *,
        tray_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Position], int]:
        conditions = []
        if tray_id:
            conditions.append(Position.tray_id == tray_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Position.code.ilike(pattern, escape="\\"),
                    Position.label.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Position.status == status)
        base = select(Position).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(Position, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Position.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def count_active_shelves(self, area_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Shelf)
            .where(Shelf.area_id == area_id, Shelf.status == "ACTIVE")
        )
        return int(result or 0)

    async def count_active_trays(self, shelf_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Tray)
            .where(Tray.shelf_id == shelf_id, Tray.status == "ACTIVE")
        )
        return int(result or 0)

    async def count_non_retired_positions(self, tray_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Position)
            .where(Position.tray_id == tray_id, Position.status != "RETIRED")
        )
        return int(result or 0)

    async def get_shelf_structure_for_update(
        self, shelf_id: UUID
    ) -> tuple[Shelf | None, Sequence[Tray], Sequence[Position]]:
        shelf = await self.session.scalar(
            select(Shelf).where(Shelf.id == shelf_id).with_for_update()
        )
        if shelf is None:
            return None, [], []
        trays = (
            await self.session.scalars(
                select(Tray)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Tray.id)
                .with_for_update()
            )
        ).all()
        positions = (
            await self.session.scalars(
                select(Position)
                .join(Tray, Tray.id == Position.tray_id)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Position.code, Position.id)
                .with_for_update()
            )
        ).all()
        return shelf, trays, positions

    async def get_shelf_structure(
        self,
        shelf_id: UUID,
    ) -> tuple[Shelf | None, Sequence[Tray], Sequence[Position]]:
        shelf = await self.session.get(Shelf, shelf_id)
        if shelf is None:
            return None, [], []
        trays = (
            await self.session.scalars(
                select(Tray).where(Tray.shelf_id == shelf_id).order_by(Tray.code, Tray.id)
            )
        ).all()
        positions = (
            await self.session.scalars(
                select(Position)
                .join(Tray, Tray.id == Position.tray_id)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Position.code, Position.id)
            )
        ).all()
        return shelf, trays, positions

    async def get_tray_structure_for_update(
        self, tray_id: UUID
    ) -> tuple[Tray | None, Sequence[Position]]:
        tray = await self.session.scalar(select(Tray).where(Tray.id == tray_id).with_for_update())
        if tray is None:
            return None, []
        positions = (
            await self.session.scalars(
                select(Position)
                .where(Position.tray_id == tray_id)
                .order_by(Position.code, Position.id)
                .with_for_update()
            )
        ).all()
        return tray, positions

    async def occupied_position_ids(
        self,
        position_ids: Sequence[UUID],
    ) -> set[UUID]:
        if not position_ids:
            return set()
        rows = await self.session.scalars(
            select(Box.current_position_id).where(Box.current_position_id.in_(position_ids))
        )
        return {row for row in rows.all() if row is not None}

    async def is_position_occupied(self, position_id: UUID) -> bool:
        result = await self.session.scalar(
            select(func.count()).select_from(Box).where(Box.current_position_id == position_id)
        )
        return bool(result)
