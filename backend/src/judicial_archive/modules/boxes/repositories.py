from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from judicial_archive.core.enums import CustodyStatus
from judicial_archive.core.text import escape_like
from judicial_archive.modules.boxes.models import Box, BoxLocationHistory


class BoxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, box_id: UUID) -> Box | None:
        return await self.session.get(Box, box_id)

    async def get_for_update(self, box_id: UUID) -> Box | None:
        return await self.session.scalar(select(Box).where(Box.id == box_id).with_for_update())

    async def get_by_visible_number(self, visible_number: str) -> Box | None:
        return await self.session.scalar(
            select(Box).where(Box.visible_number == visible_number.strip())
        )

    async def list_unlocated(
        self,
        *,
        state: str | None,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Box], int]:
        conditions: list[ColumnElement[bool]] = []
        if state == "UNASSIGNED":
            conditions.append(Box.current_position_id.is_(None))
            conditions.append(
                Box.custody_status.in_([CustodyStatus.UNKNOWN.value, CustodyStatus.MISSING.value])
            )
        elif state == "PENDING_CONFIRMATION":
            conditions.append(Box.custody_status == CustodyStatus.PENDING_VERIFICATION.value)
        else:
            conditions.append(
                or_(
                    Box.current_position_id.is_(None),
                    Box.custody_status == CustodyStatus.PENDING_VERIFICATION.value,
                )
            )
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(Box.visible_number.ilike(pattern, escape="\\"))

        base = select(Box).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = await self.session.execute(
            base.order_by(Box.visible_number.asc(), Box.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_history(
        self,
        box_id: UUID,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
        source: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[BoxLocationHistory], int]:
        conditions = [BoxLocationHistory.box_id == box_id]
        if from_date is not None:
            conditions.append(BoxLocationHistory.changed_at >= from_date)
        if to_date is not None:
            conditions.append(BoxLocationHistory.changed_at <= to_date)
        if source:
            conditions.append(BoxLocationHistory.source == source)

        base = select(BoxLocationHistory).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = await self.session.execute(
            base.order_by(
                BoxLocationHistory.changed_at.desc(),
                BoxLocationHistory.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def count_history(self, box_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(BoxLocationHistory)
            .where(BoxLocationHistory.box_id == box_id)
        )
        return int(result or 0)

    async def get_last_history_for_movement(self, movement_id: UUID) -> BoxLocationHistory | None:
        return await self.session.scalar(
            select(BoxLocationHistory)
            .where(BoxLocationHistory.movement_id == movement_id)
            .order_by(
                BoxLocationHistory.changed_at.desc(),
                BoxLocationHistory.id.desc(),
            )
            .limit(1)
        )
