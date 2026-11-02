from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import CourtStatus
from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import Court


class CourtsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, court_id: UUID) -> Court | None:
        return await self.session.get(Court, court_id)

    async def list_courts(
        self,
        *,
        q: str | None,
        status: str | None,
        court_type: str | None,
        effective_on: date | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Court], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Court.code_normalized.ilike(pattern, escape="\\"),
                    Court.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Court.status == status)
        if court_type:
            conditions.append(Court.court_type == court_type)
        if effective_on:
            conditions.append(
                or_(Court.effective_from.is_(None), Court.effective_from <= effective_on)
            )
            conditions.append(or_(Court.effective_to.is_(None), Court.effective_to >= effective_on))

        base = select(Court).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(Court, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        result = await self.session.execute(
            base.order_by(ordering, Court.id.asc()).offset(offset).limit(limit)
        )
        return result.scalars().all(), int(total or 0)

    async def count_by_normalized_code(self, code_normalized: str) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Court)
            .where(
                Court.code_normalized == code_normalized,
                Court.status == CourtStatus.ACTIVE.value,
            )
        )
        return int(result or 0)
