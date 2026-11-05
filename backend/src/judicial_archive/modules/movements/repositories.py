from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.boxes.constants import OPEN_MOVEMENT_STATUSES
from judicial_archive.modules.boxes.models import BoxMovement


class MovementsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, movement_id: UUID) -> BoxMovement | None:
        return await self.session.get(BoxMovement, movement_id)

    async def get_for_update(self, movement_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement).where(BoxMovement.id == movement_id).with_for_update()
        )

    async def get_open_for_box(self, box_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement)
            .where(
                BoxMovement.box_id == box_id,
                BoxMovement.movement_status.in_(OPEN_MOVEMENT_STATUSES),
            )
            .order_by(BoxMovement.occurred_at.desc())
            .limit(1)
        )

    async def list(
        self,
        *,
        box_id: UUID | None,
        movement_type: str | None,
        movement_status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[BoxMovement], int]:
        conditions = []
        if box_id:
            conditions.append(BoxMovement.box_id == box_id)
        if movement_type:
            conditions.append(BoxMovement.movement_type == movement_type)
        if movement_status:
            conditions.append(BoxMovement.movement_status == movement_status)
        if from_date is not None:
            conditions.append(BoxMovement.occurred_at >= from_date)
        if to_date is not None:
            conditions.append(BoxMovement.occurred_at <= to_date)

        base = select(BoxMovement).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = await self.session.execute(
            base.order_by(
                BoxMovement.occurred_at.desc(),
                BoxMovement.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def get_last_for_box(self, box_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement)
            .where(BoxMovement.box_id == box_id)
            .order_by(
                BoxMovement.occurred_at.desc(),
                BoxMovement.id.desc(),
            )
            .limit(1)
        )
