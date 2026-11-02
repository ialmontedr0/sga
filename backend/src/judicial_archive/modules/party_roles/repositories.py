from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import PartyRole

_SORT_FIELDS = frozenset({"code", "name", "status", "created_at", "updated_at"})


class PartyRolesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, item_id: UUID) -> PartyRole | None:
        return await self.session.get(PartyRole, item_id)

    async def get_by_code(self, code: str) -> PartyRole | None:
        return await self.session.scalar(select(PartyRole).where(PartyRole.code == code))

    async def list_items(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[PartyRole], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    PartyRole.code.ilike(pattern, escape="\\"),
                    PartyRole.name.ilike(pattern, escape="\\"),
                )
            )
        column = getattr(PartyRole, sort_by)
        if status:
            conditions.append(PartyRole.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(PartyRole).where(*conditions)
        )
        column = getattr(PartyRole, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(PartyRole)
                .where(*conditions)
                .order_by(ordering, PartyRole.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
