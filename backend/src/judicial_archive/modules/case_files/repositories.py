from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.case_files.models import CaseFile, CaseParty, Person
from judicial_archive.modules.courts.models import PartyRole

CaseFileMatchType = Literal["EXACT", "SUFFIX5", "SAME_YEAR"]
PersonMatchType = Literal["IDENTIFICATION", "NAME"]


class CaseFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, case_file_id: UUID) -> CaseFile | None:
        return await self.session.get(CaseFile, case_file_id)

    async def get_for_update(self, case_file_id: UUID) -> CaseFile | None:
        return await self.session.scalar(
            select(CaseFile)
            .where(CaseFile.id == case_file_id, CaseFile.deleted_at.is_(None))
            .with_for_update()
        )

    async def find_exact_nuc(
        self,
        *,
        court_id: UUID,
        nuc_normalized: str,
        exclude_id: UUID | None = None,
    ) -> CaseFile | None:
        conditions: list[ColumnElement[bool]] = [
            CaseFile.court_id == court_id,
            CaseFile.nuc_normalized == nuc_normalized,
            CaseFile.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(CaseFile.id != exclude_id)
        return await self.session.scalar(select(CaseFile).where(*conditions).limit(1))

    async def list_duplicates(
        self,
        *,
        court_id: UUID,
        nuc_normalized: str,
        year: int,
        limit: int = 20,
    ) -> Sequence[tuple[CaseFile, CaseFileMatchType]]:
        suffix5 = nuc_normalized[-5:]
        rows = await self.session.execute(
            select(CaseFile)
            .where(
                CaseFile.court_id == court_id,
                CaseFile.deleted_at.is_(None),
                or_(
                    CaseFile.nuc_normalized == nuc_normalized,
                    CaseFile.nuc_suffix5 == suffix5,
                    CaseFile.year == year,
                ),
            )
            .order_by(CaseFile.year.desc(), CaseFile.created_at.desc())
            .limit(limit)
        )
        result: list[tuple[CaseFile, CaseFileMatchType]] = []
        for row in rows.scalars().all():
            match_type: CaseFileMatchType
            if row.nuc_normalized == nuc_normalized:
                match_type = "EXACT"
            elif row.nuc_suffix5 == suffix5:
                match_type = "SUFFIX5"
            else:
                match_type = "SAME_YEAR"
            result.append((row, match_type))
        return result

    async def list_items(
        self,
        *,
        q: str | None,
        court_id: UUID | None,
        box_id: UUID | None,
        year: int | None,
        lifecycle_status: str | None,
        verification_status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[CaseFile], int]:
        allowed = {"year", "nuc_normalized", "created_at", "updated_at"}
        if sort_by not in allowed:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions: list[ColumnElement[bool]] = [CaseFile.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    CaseFile.nuc_normalized.ilike(pattern, escape="\\"),
                    CaseFile.nuc_suffix5.ilike(pattern, escape="\\"),
                    CaseFile.resolution_number.ilike(pattern, escape="\\"),
                )
            )
        if court_id is not None:
            conditions.append(CaseFile.court_id == court_id)
        if box_id is not None:
            conditions.append(CaseFile.box_id == box_id)
        if year is not None:
            conditions.append(CaseFile.year == year)
        if lifecycle_status:
            conditions.append(CaseFile.lifecycle_status == lifecycle_status)
        if verification_status:
            conditions.append(CaseFile.verification_status == verification_status)

        base = select(CaseFile).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        column = getattr(CaseFile, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                base.order_by(ordering, CaseFile.id).offset(offset).limit(limit)
            )
        ).all()
        return rows, int(total or 0)


class PersonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, person_id: UUID) -> Person | None:
        return await self.session.get(Person, person_id)

    async def get_for_update(self, person_id: UUID) -> Person | None:
        return await self.session.scalar(
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .with_for_update()
        )

    async def find_exact_identification(self, identification_number: str) -> Person | None:
        return await self.session.scalar(
            select(Person)
            .where(
                Person.identification_number == identification_number,
                Person.deleted_at.is_(None),
            )
            .limit(1)
        )

    async def list_items(
        self,
        *,
        q: str | None,
        identification_number: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Person], int]:
        conditions: list[ColumnElement[bool]] = [Person.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(Person.normalized_name.ilike(pattern, escape="\\"))
        if identification_number:
            conditions.append(Person.identification_number == identification_number.strip())
        base = select(Person).where(*conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = (
            await self.session.scalars(
                base.order_by(Person.normalized_name.asc(), Person.id.asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)

    async def list_duplicates(
        self,
        *,
        normalized_name: str,
        identification_number: str | None,
        limit: int = 20,
    ) -> Sequence[tuple[Person, PersonMatchType]]:
        conditions: list[ColumnElement[bool]] = [Person.deleted_at.is_(None)]
        if identification_number:
            conditions.append(
                or_(
                    Person.identification_number == identification_number,
                    Person.normalized_name == normalized_name,
                )
            )
        else:
            conditions.append(Person.normalized_name == normalized_name)
        rows = (
            await self.session.scalars(
                select(Person).where(*conditions).order_by(Person.created_at.desc()).limit(limit)
            )
        ).all()
        result: list[tuple[Person, PersonMatchType]] = []
        for person in rows:
            match_type: PersonMatchType
            if identification_number and person.identification_number == identification_number:
                match_type = "IDENTIFICATION"
            else:
                match_type = "NAME"
            result.append((person, match_type))
        return result


class CasePartyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, party_id: UUID) -> CaseParty | None:
        return await self.session.get(CaseParty, party_id)

    async def find_relation(
        self,
        *,
        case_file_id: UUID,
        person_id: UUID,
        party_role_id: UUID,
    ) -> CaseParty | None:
        return await self.session.scalar(
            select(CaseParty).where(
                CaseParty.case_file_id == case_file_id,
                CaseParty.person_id == person_id,
                CaseParty.party_role_id == party_role_id,
            )
        )

    async def list_for_case(
        self, case_file_id: UUID
    ) -> Sequence[tuple[CaseParty, Person, PartyRole]]:
        rows = await self.session.execute(
            select(CaseParty, Person, PartyRole)
            .join(Person, Person.id == CaseParty.person_id)
            .join(PartyRole, PartyRole.id == CaseParty.party_role_id)
            .where(CaseParty.case_file_id == case_file_id)
            .order_by(CaseParty.is_primary.desc(), Person.normalized_name.asc())
        )
        return rows.all()

    async def count_primary_for_case(self, case_file_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(CaseParty)
            .where(CaseParty.case_file_id == case_file_id, CaseParty.is_primary.is_(True))
        )
        return int(total or 0)
