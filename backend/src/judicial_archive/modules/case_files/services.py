from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    BoxType,
    LifecycleStatus,
    VerificationStatus,
)
from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.case_files import schemas
from judicial_archive.modules.case_files.models import (
    CaseFile,
    CaseFileIdentifierHistory,
    CaseParty,
    Person,
)
from judicial_archive.modules.case_files.repositories import (
    CaseFileRepository,
    CasePartyRepository,
    PersonRepository,
)
from judicial_archive.modules.case_files.validators import (
    normalize_identifier,
    normalize_person_name,
    validate_identifier,
    validate_partial_date,
)
from judicial_archive.modules.courts.models import PartyRole, ResolutionType
from judicial_archive.modules.users.models import User


def _case_snapshot(case_file: CaseFile) -> dict[str, object]:
    return {
        "court_id": str(case_file.court_id),
        "box_id": str(case_file.box_id) if case_file.box_id else None,
        "nuc_raw": case_file.nuc_raw,
        "nuc_normalized": case_file.nuc_normalized,
        "year": case_file.year,
        "resolution_number": case_file.resolution_number,
        "verification_status": case_file.verification_status,
        "lifecycle_status": case_file.lifecycle_status,
        "version": case_file.version,
    }


async def _validate_box_for_content(
    session: AsyncSession,
    *,
    box_id: UUID,
    expected_type: str,
    lock: bool = True,
) -> Box:
    repo = BoxRepository(session)
    box = await repo.get_for_update(box_id) if lock else await repo.get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError(
            "La caja no esta activa.",
            details={"reason": "box_not_active"},
        )
    if box.box_type != expected_type:
        raise InvalidParameterError(
            "El tipo de caja no coincide con el contenido.",
            details={"reason": "box_type_mismatch"},
        )
    return box


async def _validate_resolution(
    session: AsyncSession,
    *,
    court_id: UUID,
    body: schemas.CaseFileInlineCreate,
) -> None:
    if body.resolution_type_id is not None:
        resolution = await session.get(ResolutionType, body.resolution_type_id)
        if resolution is None:
            raise NotFoundError("Tipo de resolucion no encontrado.")
        if resolution.status != "ACTIVE":
            raise InvalidParameterError("El tipo de resolucion esta inactivo.")

    if body.resolution_number:
        await validate_identifier(
            session,
            court_id=court_id,
            kind="SENTENCE",
            raw_value=body.resolution_number,
            allow_exception=body.historical_exception,
            exception_reason=body.exception_reason,
        )

    validate_partial_date(
        precision=body.entry_precision,
        year=body.entry_year,
        month=body.entry_month,
        day=body.entry_day,
        field="entry",
    )
    validate_partial_date(
        precision=body.sentence_precision,
        year=body.sentence_year,
        month=body.sentence_month,
        day=body.sentence_day,
        field="sentence",
    )


async def prepare_case_file(
    session: AsyncSession,
    *,
    actor: User,
    court_id: UUID,
    box_id: UUID | None,
    body: schemas.CaseFileInlineCreate,
    box: Box | None = None,
) -> tuple[CaseFile, list[str]]:
    warnings: list[str] = []
    if box is not None:
        if box.id != box_id:
            raise InvalidParameterError("La caja no coincide con el contenido.")
        if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
            raise ConflictError("La caja no esta activa.", details={"reason": "box_not_active"})
        if box.box_type != BoxType.EXPEDIENTES.value:
            raise InvalidParameterError(
                "Un expediente solo puede pertenecer a una caja de expedientes.",
                details={"reason": "box_type_mismatch"},
            )
    elif box_id is not None:
        await _validate_box_for_content(
            session,
            box_id=box_id,
            expected_type=BoxType.EXPEDIENTES.value,
        )

    await _validate_resolution(session, court_id=court_id, body=body)

    nuc = await validate_identifier(
        session,
        court_id=court_id,
        kind="NUC",
        raw_value=body.nuc,
        allow_exception=body.historical_exception,
        exception_reason=body.exception_reason,
    )
    if nuc.warning:
        warnings.append(nuc.warning)

    repo = CaseFileRepository(session)
    duplicate = await repo.find_exact_nuc(
        court_id=court_id,
        nuc_normalized=nuc.normalized,
    )
    if duplicate is not None:
        if not body.duplicate_override:
            raise ConflictError(
                "Ya existe un expediente con el mismo NUC en el tribunal.",
                details={
                    "reason": "duplicate_nuc",
                    "case_file_id": str(duplicate.id),
                },
            )
        if not (body.duplicate_override_reason or "").strip():
            raise InvalidParameterError(
                "La excepcion de duplicado requiere motivo.",
                details={"reason": "duplicate_override_reason_required"},
            )
        warnings.append("Se registro un NUC duplicado como excepcion auditada.")

    verification_status = nuc.verification_status
    if duplicate is not None:
        verification_status = VerificationStatus.CONFLICT.value

    case_file = CaseFile(
        court_id=court_id,
        box_id=box_id,
        box_type=BoxType.EXPEDIENTES.value,
        nuc_raw=nuc.raw,
        nuc_normalized=nuc.normalized,
        year=body.year,
        entry_precision=body.entry_precision,
        entry_year=body.entry_year,
        entry_month=body.entry_month,
        entry_day=body.entry_day,
        sentence_precision=body.sentence_precision,
        sentence_year=body.sentence_year,
        sentence_month=body.sentence_month,
        sentence_day=body.sentence_day,
        resolution_type_id=body.resolution_type_id,
        resolution_number=clean_optional_text(body.resolution_number, max_length=100),
        judge_name=clean_optional_text(body.judge_name, max_length=200),
        court_name_raw=clean_optional_text(body.court_name_raw, max_length=200),
        description=clean_optional_text(body.description, max_length=1000),
        verification_status=verification_status,
        confidentiality=body.confidentiality,
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        source=clean_optional_text(body.source, max_length=32),
        notes=clean_optional_text(body.notes, max_length=2000),
        created_by=actor.id,
    )
    session.add(case_file)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "No se pudo crear el expediente por una restriccion de integridad.",
            details={"reason": "case_file_integrity_conflict"},
        ) from exc

    session.add(
        CaseFileIdentifierHistory(
            case_file_id=case_file.id,
            identifier_kind="NUC",
            value_raw=nuc.raw,
            value_normalized=nuc.normalized,
            is_primary=True,
            reason="Alta inicial del expediente.",
            changed_by=actor.id,
        )
    )

    for party in body.parties:
        await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=party,
            actor=actor,
        )

    return case_file, warnings


async def _prepare_party(
    session: AsyncSession,
    *,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
    actor: User,
) -> CaseParty:
    person = await PersonRepository(session).get(body.person_id)
    if person is None or person.deleted_at is not None:
        raise NotFoundError("Persona no encontrada.")
    role = await session.get(PartyRole, body.party_role_id)
    if role is None:
        raise NotFoundError("Rol de parte no encontrado.")
    if role.status != "ACTIVE":
        raise InvalidParameterError("El rol de parte esta inactivo.")

    repo = CasePartyRepository(session)
    existing = await repo.find_relation(
        case_file_id=case_file_id,
        person_id=body.person_id,
        party_role_id=body.party_role_id,
    )
    if existing is not None:
        raise ConflictError(
            "La persona ya esta relacionada con ese rol en el expediente.",
            details={"reason": "duplicate_case_party"},
        )
    if body.is_primary and await repo.count_primary_for_case(case_file_id) > 0:
        raise ConflictError(
            "El expediente ya tiene una parte principal.",
            details={"reason": "primary_party_exists"},
        )

    party = CaseParty(
        case_file_id=case_file_id,
        person_id=body.person_id,
        party_role_id=body.party_role_id,
        is_primary=body.is_primary,
        notes=clean_optional_text(body.notes, max_length=1000),
        created_by=actor.id,
    )
    session.add(party)
    await session.flush()
    return party


async def create_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.CaseFileCreate,
) -> schemas.CaseFileDetailOut:
    try:
        case_file, warnings = await prepare_case_file(
            session,
            actor=actor,
            court_id=body.court_id,
            box_id=body.box_id,
            body=body,
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.created",
            entity_type="case_file",
            entity_id=case_file.id,
            after=_case_snapshot(case_file),
            metadata={
                "warnings": warnings,
                "historical_exception": body.historical_exception,
                "exception_reason": body.exception_reason,
                "duplicate_override": body.duplicate_override,
                "duplicate_override_reason": body.duplicate_override_reason,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id, warnings=warnings)


def _party_out(
    party: CaseParty,
    person: Person,
    role: PartyRole,
) -> schemas.CasePartyOut:
    return schemas.CasePartyOut(
        id=party.id,
        case_file_id=party.case_file_id,
        person=schemas.PersonOut.model_validate(person),
        party_role_id=role.id,
        party_role_code=role.code,
        party_role_name=role.name,
        is_primary=party.is_primary,
        notes=party.notes,
        created_at=party.created_at,
        updated_at=party.updated_at,
    )


async def get_case_file_detail(
    session: AsyncSession,
    case_file_id: UUID,
    *,
    warnings: list[str] | None = None,
) -> schemas.CaseFileDetailOut:
    case_file = await CaseFileRepository(session).get(case_file_id)
    if case_file is None or case_file.deleted_at is not None:
        raise NotFoundError("Expediente no encontrado.")
    rows = await CasePartyRepository(session).list_for_case(case_file.id)
    base = schemas.CaseFileOut.model_validate(case_file)
    return schemas.CaseFileDetailOut(
        **base.model_dump(),
        parties=[_party_out(party, person, role) for party, person, role in rows],
        warnings=warnings or [],
    )


async def list_case_files(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    court_id: UUID | None,
    box_id: UUID | None,
    year: int | None,
    lifecycle_status: str | None,
    verification_status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.CaseFileOut]:
    rows, total = await CaseFileRepository(session).list_items(
        q=q,
        court_id=court_id,
        box_id=box_id,
        year=year,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.CaseFileOut.model_validate(row) for row in rows]
    return Page[schemas.CaseFileOut].build(items, total=total, params=params)


async def get_case_file(
    session: AsyncSession,
    case_file_id: UUID,
) -> schemas.CaseFileDetailOut:
    return await get_case_file_detail(session, case_file_id)


async def update_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileUpdate,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": case_file.version},
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no puede modificarse.",
                details={"reason": "case_file_voided"},
            )

        before = _case_snapshot(case_file)
        changes = body.model_dump(exclude_unset=True)
        changes.pop("expected_version", None)

        if "box_id" in changes:
            new_box_id = changes["box_id"]
            if new_box_id != case_file.box_id:
                if not (body.change_reason or "").strip():
                    raise InvalidParameterError(
                        "El cambio de caja requiere motivo.",
                        details={"reason": "change_reason_required"},
                    )
                if new_box_id is not None:
                    await _validate_box_for_content(
                        session,
                        box_id=new_box_id,
                        expected_type=BoxType.EXPEDIENTES.value,
                    )
                case_file.box_id = new_box_id
                case_file.box_type = BoxType.EXPEDIENTES.value

        if "resolution_type_id" in changes and changes["resolution_type_id"] is not None:
            resolution = await session.get(ResolutionType, changes["resolution_type_id"])
            if resolution is None:
                raise NotFoundError("Tipo de resolucion no encontrado.")
            if resolution.status != "ACTIVE":
                raise InvalidParameterError("El tipo de resolucion esta inactivo.")

        if "resolution_number" in changes:
            raw_resolution = changes["resolution_number"]
            previous_resolution = case_file.resolution_number
            if raw_resolution:
                sentence = await validate_identifier(
                    session,
                    court_id=case_file.court_id,
                    kind="SENTENCE",
                    raw_value=raw_resolution,
                )
                case_file.resolution_number = sentence.normalized
                if previous_resolution != sentence.normalized:
                    session.add(
                        CaseFileIdentifierHistory(
                            case_file_id=case_file.id,
                            identifier_kind="SENTENCE",
                            value_raw=sentence.raw,
                            value_normalized=sentence.normalized,
                            is_primary=False,
                            reason=(body.change_reason or "Actualizacion de resolucion").strip(),
                            changed_by=actor.id,
                        )
                    )
            else:
                case_file.resolution_number = None

        for field in (
            "entry_precision",
            "entry_year",
            "entry_month",
            "entry_day",
            "sentence_precision",
            "sentence_year",
            "sentence_month",
            "sentence_day",
        ):
            if field in changes:
                setattr(case_file, field, changes[field])

        if "resolution_type_id" in changes:
            case_file.resolution_type_id = changes["resolution_type_id"]
        for field, max_length in (
            ("judge_name", 200),
            ("court_name_raw", 200),
            ("notes", 2000),
        ):
            if field in changes:
                setattr(
                    case_file,
                    field,
                    clean_optional_text(changes[field], max_length=max_length),
                )
        if "description" in changes:
            case_file.description = clean_optional_text(changes["description"], max_length=1000)
        if "confidentiality" in changes and changes["confidentiality"] is not None:
            case_file.confidentiality = changes["confidentiality"]

        validate_partial_date(
            precision=case_file.entry_precision,
            year=case_file.entry_year,
            month=case_file.entry_month,
            day=case_file.entry_day,
            field="entry",
        )
        validate_partial_date(
            precision=case_file.sentence_precision,
            year=case_file.sentence_year,
            month=case_file.sentence_month,
            day=case_file.sentence_day,
            field="sentence",
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.updated",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"change_reason": body.change_reason},
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "El expediente fue modificado por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def add_party(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
) -> schemas.CasePartyOut:
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite partes.")
        party = await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=body,
            actor=actor,
        )
        party_id = party.id
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.added",
            entity_type="case_party",
            entity_id=party.id,
            after={
                "case_file_id": str(case_file_id),
                "person_id": str(party.person_id),
                "party_role_id": str(party.party_role_id),
                "is_primary": party.is_primary,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    rows = await CasePartyRepository(session).list_for_case(case_file_id)
    for party, person, role in rows:
        if party.id == party_id:
            return _party_out(party, person, role)
    raise NotFoundError("Parte no encontrada.")


async def add_party_with_person(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CasePartyWithPersonCreate,
) -> schemas.CasePartyOut:
    person_repo = PersonRepository(session)
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite partes.")

        normalized_name = normalize_person_name(body.person.display_name)
        identification = clean_optional_text(body.person.identification_number, max_length=64)
        if identification:
            identification = identification.strip().upper()
            existing = await person_repo.find_exact_identification(identification)
            if existing is not None:
                raise ConflictError(
                    "Ya existe una persona con ese numero de identificacion.",
                    details={"reason": "duplicate_person", "person_id": str(existing.id)},
                )

        person = Person(
            display_name=" ".join(body.person.display_name.strip().split()),
            normalized_name=normalized_name,
            aliases=body.person.aliases,
            identification_type=clean_optional_text(body.person.identification_type, max_length=32),
            identification_number=identification,
            birth_year=body.person.birth_year,
            birth_month=body.person.birth_month,
            birth_day=body.person.birth_day,
            notes=clean_optional_text(body.person.notes, max_length=2000),
            created_by=actor.id,
        )
        session.add(person)
        await session.flush()

        party_body = schemas.CasePartyCreate(
            person_id=person.id,
            party_role_id=body.party_role_id,
            is_primary=body.is_primary,
            notes=body.notes,
        )
        party = await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=party_body,
            actor=actor,
        )
        person_id = person.id
        party_id = party.id
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="person.created",
            entity_type="person",
            entity_id=person.id,
            after={"display_name": person.display_name, "normalized_name": person.normalized_name},
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.added",
            entity_type="case_party",
            entity_id=party.id,
            after={
                "case_file_id": str(case_file.id),
                "person_id": str(person.id),
                "party_role_id": str(party.party_role_id),
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    rows = await CasePartyRepository(session).list_for_case(case_file_id)
    for party, person, role in rows:
        if party.id == party_id and party.person_id == person_id:
            return _party_out(party, person, role)
    raise NotFoundError("Parte no encontrada.")


async def remove_party(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    party_id: UUID,
) -> None:
    repo = CasePartyRepository(session)
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite cambios de partes.")
        party = await repo.get(party_id)
        if party is None or party.case_file_id != case_file_id:
            raise NotFoundError("Parte no encontrada.")
        before = {
            "person_id": str(party.person_id),
            "party_role_id": str(party.party_role_id),
            "is_primary": party.is_primary,
        }
        await session.delete(party)
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.removed",
            entity_type="case_party",
            entity_id=party_id,
            before=before,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def correct_identifier(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileIdentifierCorrection,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": case_file.version},
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no admite correcciones.",
                details={"reason": "case_file_voided"},
            )
        before = _case_snapshot(case_file)
        previous: str | None
        if body.identifier_kind == "NUC":
            validation = await validate_identifier(
                session,
                court_id=case_file.court_id,
                kind="NUC",
                raw_value=body.value,
                allow_exception=body.historical_exception,
                exception_reason=body.exception_reason,
            )
            duplicate = await repo.find_exact_nuc(
                court_id=case_file.court_id,
                nuc_normalized=validation.normalized,
                exclude_id=case_file.id,
            )
            if duplicate is not None:
                raise ConflictError(
                    "Ya existe otro expediente con ese NUC.",
                    details={"reason": "duplicate_nuc", "case_file_id": str(duplicate.id)},
                )
            previous = case_file.nuc_raw
            case_file.nuc_raw = validation.raw
            case_file.nuc_normalized = validation.normalized
            case_file.verification_status = validation.verification_status
        else:
            validation = await validate_identifier(
                session,
                court_id=case_file.court_id,
                kind="SENTENCE",
                raw_value=body.value,
                allow_exception=body.historical_exception,
                exception_reason=body.exception_reason,
            )
            previous = case_file.resolution_number
            case_file.resolution_number = validation.normalized
            if validation.verification_status == VerificationStatus.CONFLICT.value:
                case_file.verification_status = validation.verification_status

        session.add(
            CaseFileIdentifierHistory(
                case_file_id=case_file.id,
                identifier_kind=body.identifier_kind,
                value_raw=validation.raw,
                value_normalized=validation.normalized,
                is_primary=body.identifier_kind == "NUC",
                reason=body.reason.strip(),
                changed_by=actor.id,
            )
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.identifier_corrected",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={
                "identifier_kind": body.identifier_kind,
                "previous_value": previous,
                "new_value": validation.normalized,
                "reason": body.reason.strip(),
                "historical_exception": body.historical_exception,
            },
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "El expediente fue modificado por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def relocate_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileRelocate,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": case_file.version},
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no puede reubicarse.")
        await _validate_box_for_content(
            session,
            box_id=body.box_id,
            expected_type=BoxType.EXPEDIENTES.value,
        )
        before = _case_snapshot(case_file)
        case_file.box_id = body.box_id
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.relocated",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def archive_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
) -> schemas.CaseFileDetailOut:
    return await _change_case_lifecycle(
        request,
        session,
        actor,
        case_file_id,
        body,
        target=LifecycleStatus.ARCHIVED.value,
        action="case_file.archived",
    )


async def void_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
) -> schemas.CaseFileDetailOut:
    return await _change_case_lifecycle(
        request,
        session,
        actor,
        case_file_id,
        body,
        target=LifecycleStatus.VOIDED.value,
        action="case_file.voided",
    )


async def _change_case_lifecycle(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    *,
    target: str,
    action: str,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": case_file.version},
            )
        before = _case_snapshot(case_file)
        if target == LifecycleStatus.ARCHIVED.value:
            if case_file.lifecycle_status != LifecycleStatus.ACTIVE.value:
                raise ConflictError(
                    "Solo un expediente activo puede archivarse.",
                    details={"reason": "case_file_not_active"},
                )
            case_file.lifecycle_status = target
            case_file.archived_at = datetime.now(UTC)
            case_file.archived_by = actor.id
            case_file.archive_reason = body.reason.strip()
        else:
            if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
                raise ConflictError("El expediente ya esta anulado.")
            case_file.lifecycle_status = target
            case_file.voided_at = datetime.now(UTC)
            case_file.voided_by = actor.id
            case_file.void_reason = body.reason.strip()
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action=action,
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def soft_delete_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileDeleteRequest,
) -> None:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": case_file.version},
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no puede darse de baja.",
                details={"reason": "case_file_voided"},
            )
        before = _case_snapshot(case_file)
        case_file.deleted_at = datetime.now(UTC)
        case_file.deleted_by = actor.id
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.deleted",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def list_case_file_duplicates(
    session: AsyncSession,
    *,
    court_id: UUID,
    nuc: str,
    year: int,
    limit: int = 20,
) -> list[schemas.DuplicateCaseFileOut]:
    normalized = normalize_identifier(nuc)
    rows = await CaseFileRepository(session).list_duplicates(
        court_id=court_id,
        nuc_normalized=normalized,
        year=year,
        limit=limit,
    )
    return [
        schemas.DuplicateCaseFileOut(
            id=case_file.id,
            nuc_raw=case_file.nuc_raw,
            nuc_normalized=case_file.nuc_normalized,
            nuc_suffix5=case_file.nuc_suffix5,
            court_id=case_file.court_id,
            year=case_file.year,
            box_id=case_file.box_id,
            match_type=match_type,
            verification_status=case_file.verification_status,
        )
        for case_file, match_type in rows
    ]


async def list_persons(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    identification_number: str | None,
) -> Page[schemas.PersonOut]:
    rows, total = await PersonRepository(session).list_items(
        q=q,
        identification_number=identification_number,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PersonOut.model_validate(row) for row in rows]
    return Page[schemas.PersonOut].build(items, total=total, params=params)


async def get_person(session: AsyncSession, person_id: UUID) -> schemas.PersonOut:
    person = await PersonRepository(session).get(person_id)
    if person is None or person.deleted_at is not None:
        raise NotFoundError("Persona no encontrada.")
    return schemas.PersonOut.model_validate(person)


async def list_person_duplicates(
    session: AsyncSession,
    *,
    display_name: str,
    identification_number: str | None,
    limit: int = 20,
) -> list[schemas.DuplicatePersonOut]:
    rows = await PersonRepository(session).list_duplicates(
        normalized_name=normalize_person_name(display_name),
        identification_number=clean_optional_text(identification_number, max_length=64),
        limit=limit,
    )
    return [
        schemas.DuplicatePersonOut(
            id=person.id,
            display_name=person.display_name,
            normalized_name=person.normalized_name,
            identification_number=person.identification_number,
            match_type=match_type,
        )
        for person, match_type in rows
    ]
