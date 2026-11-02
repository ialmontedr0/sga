from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.courts.models import IdentifierFormatProfile


class IdentifierProfilesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, profile_id: UUID) -> IdentifierFormatProfile | None:
        return await self.session.get(IdentifierFormatProfile, profile_id)

    async def get_active_for_update(
        self, court_id: UUID, kind: str
    ) -> IdentifierFormatProfile | None:
        return await self.session.scalar(
            select(IdentifierFormatProfile)
            .where(
                IdentifierFormatProfile.court_id == court_id,
                IdentifierFormatProfile.identifier_kind == kind,
                IdentifierFormatProfile.is_active.is_(True),
            )
            .with_for_update()
        )

    async def list_profiles(
        self,
        *,
        court_id: UUID | None,
        identifier_kind: str | None,
        is_active: bool | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[IdentifierFormatProfile], int]:
        conditions = []
        if court_id is not None:
            conditions.append(IdentifierFormatProfile.court_id == court_id)
        if identifier_kind is not None:
            conditions.append(IdentifierFormatProfile.identifier_kind == identifier_kind)
        if is_active is not None:
            conditions.append(IdentifierFormatProfile.is_active.is_(is_active))

        total = await self.session.scalar(
            select(func.count()).select_from(IdentifierFormatProfile).where(*conditions)
        )
        rows = (
            await self.session.scalars(
                select(IdentifierFormatProfile)
                .where(*conditions)
                .order_by(IdentifierFormatProfile.effective_from.desc(), IdentifierFormatProfile.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
