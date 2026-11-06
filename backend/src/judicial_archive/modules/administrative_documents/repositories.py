from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.administrative_documents.models import AdministrativeDocument


class AdministrativeDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, document_id: UUID) -> AdministrativeDocument | None:
        return await self.session.get(AdministrativeDocument, document_id)

    async def get_for_update(self, document_id: UUID) -> AdministrativeDocument | None:
        return await self.session.scalar(
            select(AdministrativeDocument)
            .where(
                AdministrativeDocument.id == document_id,
                AdministrativeDocument.deleted_at.is_(None),
            )
            .with_for_update()
        )

    async def find_duplicate(
        self,
        *,
        box_id: UUID,
        title: str,
        document_year: int,
        exclude_id: UUID | None = None,
    ) -> AdministrativeDocument | None:
        conditions: list[ColumnElement[bool]] = [
            AdministrativeDocument.box_id == box_id,
            AdministrativeDocument.document_year == document_year,
            func.lower(AdministrativeDocument.title) == title.strip().lower(),
            AdministrativeDocument.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(AdministrativeDocument.id != exclude_id)
        return await self.session.scalar(select(AdministrativeDocument).where(*conditions).limit(1))

    async def list_items(
        self,
        *,
        q: str | None,
        box_id: UUID | None,
        document_year: int | None,
        lifecycle_status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[AdministrativeDocument], int]:
        allowed = {"document_year", "title", "created_at", "updated_at"}
        if sort_by not in allowed:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions: list[ColumnElement[bool]] = [AdministrativeDocument.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    AdministrativeDocument.title.ilike(pattern, escape="\\"),
                    AdministrativeDocument.description.ilike(pattern, escape="\\"),
                )
            )
        if box_id is not None:
            conditions.append(AdministrativeDocument.box_id == box_id)
        if document_year is not None:
            conditions.append(AdministrativeDocument.document_year == document_year)
        if lifecycle_status:
            conditions.append(AdministrativeDocument.lifecycle_status == lifecycle_status)
        base = select(AdministrativeDocument).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(AdministrativeDocument, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                base.order_by(ordering, AdministrativeDocument.id).offset(offset).limit(limit)
            )
        ).all()
        return rows, int(total or 0)
