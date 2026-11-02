from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import SystemSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_key(self, key: str) -> SystemSetting | None:
        return await self.session.scalar(select(SystemSetting).where(SystemSetting.key == key))

    async def get_by_key_for_update(self, key: str) -> SystemSetting | None:
        return await self.session.scalar(
            select(SystemSetting).where(SystemSetting.key == key).with_for_update()
        )

    async def list_items(
        self, *, q: str | None, value_type: str | None, offset: int, limit: int
    ) -> tuple[Sequence[SystemSetting], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    SystemSetting.key.ilike(pattern, escape="\\"),
                    SystemSetting.description.ilike(pattern, escape="\\"),
                )
            )
        if value_type:
            conditions.append(SystemSetting.value_type == value_type)

        total = await self.session.scalar(
            select(func.count()).select_from(SystemSetting).where(*conditions)
        )
        rows = (
            await self.session.scalars(
                select(SystemSetting)
                .where(*conditions)
                .order_by(SystemSetting.key, SystemSetting.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
