from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import ResolutionType

_SORT_FIELDS = frozenset({"code", "name", "status", "created_at", "updated_at"})


class ResolutionTypesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, item_id: UUID) -> ResolutionType | None:
        return await self.session.get(ResolutionType, item_id)

    async def get_by_code(self, code: str) -> ResolutionType | None:
        return await self.session.scalar(select(ResolutionType).where(ResolutionType.code == code))

    async def list_items(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[ResolutionType], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido")

        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    ResolutionType.code.ilike(pattern, escape="\\"),
                    ResolutionType.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(ResolutionType.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(ResolutionType).where(*conditions)
        )
        column = getattr(ResolutionType, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(ResolutionType)
                .where(*conditions)
                .order_by(ordering, ResolutionType.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
