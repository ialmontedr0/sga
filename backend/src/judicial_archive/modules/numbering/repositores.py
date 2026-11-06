from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import NumberingPolicy

_SORT_FIELDS = frozenset(
    {"code", "scope", "is_active", "effective_from", "effective_to", "created_at", "updated_at"}
)


class NumberingPoliciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, policy_id: UUID) -> NumberingPolicy | None:
        return await self.session.get(NumberingPolicy, policy_id)

    async def get_by_code(self, code: str) -> NumberingPolicy | None:
        return await self.session.scalar(
            select(NumberingPolicy).where(NumberingPolicy.code == code)
        )

    async def get_by_sequence_name(self, name: str) -> NumberingPolicy | None:
        return await self.session.scalar(
            select(NumberingPolicy).where(NumberingPolicy.sequence_name == name)
        )

    async def get_active_for_update(
        self,
        *,
        scope: str,
        court_id: UUID | None,
        box_type: str | None,
        year: int | None,
    ) -> NumberingPolicy | None:
        conditions = [NumberingPolicy.scope == scope, NumberingPolicy.is_active.is_(True)]
        if scope == "COURT":
            conditions.append(NumberingPolicy.court_id == court_id)
        elif scope == "BOX_TYPE":
            conditions.append(NumberingPolicy.box_type == box_type)
        elif scope == "YEAR":
            conditions.append(NumberingPolicy.year == year)
        return await self.session.scalar(
            select(NumberingPolicy).where(*conditions).with_for_update()
        )

    async def list_items(
        self,
        *,
        q: str | None,
        scope: str | None,
        is_active: bool | None,
        court_id: UUID | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[NumberingPolicy], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido.")

        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    NumberingPolicy.code.ilike(pattern, escape="\\"),
                    NumberingPolicy.description.ilike(pattern, escape="\\"),
                )
            )
        if scope:
            conditions.append(NumberingPolicy.scope == scope)
        if is_active is not None:
            conditions.append(NumberingPolicy.is_active == is_active)
        if court_id is not None:
            conditions.append(NumberingPolicy.court_id == court_id)

        total = await self.session.scalar(
            select(func.count()).select_from(NumberingPolicy).where(*conditions)
        )
        column = getattr(NumberingPolicy, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(NumberingPolicy)
                .where(*conditions)
                .order_by(ordering, NumberingPolicy.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)

    async def list_active_candidates(
        self,
        *,
        court_id: UUID,
        box_type: str,
        year: int,
        on_date: date,
    ) -> Sequence[NumberingPolicy]:
        rows = await self.session.scalars(
            select(NumberingPolicy).where(
                NumberingPolicy.is_active.is_(True),
                NumberingPolicy.effective_from <= on_date,
                or_(
                    NumberingPolicy.effective_to.is_(None),
                    NumberingPolicy.effective_to >= on_date,
                ),
                or_(
                    NumberingPolicy.scope == "GLOBAL",
                    (NumberingPolicy.scope == "COURT") & (NumberingPolicy.court_id == court_id),
                    (NumberingPolicy.scope == "BOX_TYPE") & (NumberingPolicy.box_type == box_type),
                    (NumberingPolicy.scope == "YEAR") & (NumberingPolicy.year == year),
                ),
            )
        )
        return rows.all()
