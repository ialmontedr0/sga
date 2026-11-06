from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import BoxLifecycleStatus, BoxType, CourtStatus
from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.administrative_documents.services import (
    prepare_administrative_document,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes import schemas
from judicial_archive.modules.boxes.models import Box, BoxNumberHistory
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.case_files.services import prepare_case_file
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.numbering.services import allocate_visible_number
from judicial_archive.modules.users.models import User


def _snapshot(box: Box) -> dict[str, object]:
    return {
        "visible_number": box.visible_number,
        "court_id": str(box.court_id),
        "year": box.year,
        "box_type": box.box_type,
        "description": box.description,
        "confidentiality": box.confidentiality,
        "lifecycle_status": box.lifecycle_status,
        "custody_status": box.custody_status,
        "version": box.version,
    }


async def _active_court(session: AsyncSession, court_id: UUID) -> Court:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    if court.status != CourtStatus.ACTIVE.value:
        raise InvalidParameterError("El tribunal esta inactivo.")
    return court


async def _insert_box(
    session: AsyncSession,
    *,
    actor: User,
    body: schemas.BoxCreate,
) -> Box:
    await _active_court(session, body.court_id)

    if body.visible_number is not None:
        visible_number = body.visible_number.strip()
        policy_id = body.numbering_policy_id
    else:
        visible_number, policy = await allocate_visible_number(
            session,
            court_id=body.court_id,
            box_type=body.box_type,
            year=body.year,
            policy_id=body.numbering_policy_id,
        )
        policy_id = policy.id

    box = Box(
        court_id=body.court_id,
        year=body.year,
        box_type=body.box_type,
        visible_number=visible_number,
        numbering_policy_id=policy_id,
        description=clean_optional_text(body.description, max_length=500),
        confidentiality=body.confidentiality,
        lifecycle_status=BoxLifecycleStatus.ACTIVE.value,
        created_by=actor.id,
    )
    session.add(box)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "Ya existe una caja con ese numero visible.",
            details={"reason": "duplicate_visible_number"},
        ) from exc
    return box


async def create_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.BoxCreate,
) -> schemas.BoxOut:
    try:
        box = await _insert_box(session, actor=actor, body=body)
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.created",
            entity_type="box",
            entity_id=box.id,
            after=_snapshot(box),
            metadata=(
                {"historical_exception": True, "reason": body.exception_reason}
                if body.historical_exception
                else None
            ),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def list_boxes(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    court_id: UUID | None,
    year: int | None,
    box_type: str | None,
    lifecycle_status: str | None,
    custody_status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.BoxOut]:
    rows, total = await BoxRepository(session).list_items(
        q=q,
        court_id=court_id,
        year=year,
        box_type=box_type,
        lifecycle_status=lifecycle_status,
        custody_status=custody_status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.BoxOut.model_validate(row) for row in rows]
    return Page[schemas.BoxOut].build(items, total=total, params=params)


async def get_box(session: AsyncSession, box_id: UUID) -> schemas.BoxOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    return schemas.BoxOut.model_validate(box)


async def update_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.BoxUpdate,
) -> schemas.BoxOut:
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        before = _snapshot(box)
        changes = body.model_dump(exclude_unset=True)
        if "description" in changes:
            box.description = clean_optional_text(changes["description"], max_length=500)
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.updated",
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "La caja fue modificada por otro usuario.", details={"reason": "stale_version"}
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def correct_box_number(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.BoxNumberCorrection,
) -> schemas.BoxOut:
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        new_number = body.visible_number.strip()
        if not new_number:
            raise InvalidParameterError("El numero visible no puede estar vacio.")
        if new_number == box.visible_number:
            raise InvalidParameterError("El nuevo numero debe ser diferente al actual.")
        before = _snapshot(box)
        previous = box.visible_number
        box.visible_number = new_number
        session.add(
            BoxNumberHistory(
                box_id=box.id,
                previous_number=previous,
                new_number=new_number,
                reason=body.reason.strip(),
                changed_by=actor.id,
            )
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.number_corrected",
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Ya existe una caja con ese numero visible.",
            details={"reason": "duplicate_visible_number"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def set_box_lifecycle(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    *,
    target: str,
    body: schemas.BoxLifecycleRequest,
) -> schemas.BoxOut:
    if target not in {BoxLifecycleStatus.ARCHIVED.value, BoxLifecycleStatus.VOIDED.value}:
        raise InvalidParameterError("Transicion de caja no permitida.")
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
            raise ConflictError(
                "Solo una caja activa puede archivarse o anularse.",
                details={"reason": "box_not_active"},
            )
        if await repo.has_open_movement(box.id):
            raise ConflictError(
                "La caja tiene un movimiento abierto.",
                details={"reason": "open_movement_exists"},
            )
        before = _snapshot(box)
        now = datetime.now(UTC)
        if target == BoxLifecycleStatus.ARCHIVED.value:
            box.lifecycle_status = target
            box.archived_at = now
            box.archived_by = actor.id
            box.archive_reason = body.reason.strip()
            action = "box.archived"
        else:
            box.lifecycle_status = target
            box.voided_at = now
            box.voided_by = actor.id
            box.void_reason = body.reason.strip()
            action = "box.voided"
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action=action,
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def create_box_with_content(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.BoxWithContentCreate,
) -> schemas.BoxWithContentOut:
    case_file_ids: list[UUID] = []
    administrative_document_ids: list[UUID] = []
    warnings: list[str] = []
    try:
        box = await _insert_box(session, actor=actor, body=body.box)

        if box.box_type == BoxType.EXPEDIENTES.value:
            for case_inline in body.case_files:
                case_file, case_warnings = await prepare_case_file(
                    session,
                    actor=actor,
                    court_id=box.court_id,
                    box_id=box.id,
                    body=case_inline,
                    box=box,
                )
                case_file_ids.append(case_file.id)
                warnings.extend(case_warnings)
                await record_audit_event(
                    session,
                    request=request,
                    actor=actor,
                    action="case_file.created",
                    entity_type="case_file",
                    entity_id=case_file.id,
                    after={
                        "court_id": str(case_file.court_id),
                        "box_id": str(case_file.box_id) if case_file.box_id else None,
                        "nuc_raw": case_file.nuc_raw,
                        "nuc_normalized": case_file.nuc_normalized,
                        "year": case_file.year,
                        "verification_status": case_file.verification_status,
                    },
                    metadata={
                        "box_id": str(box.id),
                        "atomic_box_creation": True,
                        "warnings": case_warnings,
                    },
                )
        else:
            for document_inline in body.administrative_documents:
                document, doc_warnings = await prepare_administrative_document(
                    session,
                    actor=actor,
                    box=box,
                    body=document_inline,
                )
                administrative_document_ids.append(document.id)
                warnings.extend(doc_warnings)
                await record_audit_event(
                    session,
                    request=request,
                    actor=actor,
                    action="administrative_document.created",
                    entity_type="administrative_document",
                    entity_id=document.id,
                    after={
                        "box_id": str(document.box_id),
                        "title": document.title,
                        "document_type": document.document_type,
                        "document_year": document.document_year,
                        "verification_status": document.verification_status,
                    },
                    metadata={
                        "box_id": str(box.id),
                        "atomic_box_creation": True,
                        "warnings": doc_warnings,
                    },
                )

        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.created_with_content",
            entity_type="box",
            entity_id=box.id,
            after=_snapshot(box),
            metadata={
                "case_file_ids": [str(item) for item in case_file_ids],
                "administrative_document_ids": [str(item) for item in administrative_document_ids],
                "warnings": warnings,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxWithContentOut(
        box=schemas.BoxOut.model_validate(box),
        case_file_ids=case_file_ids,
        administrative_document_ids=administrative_document_ids,
        warnings=warnings,
    )


async def get_box_content_summary(
    session: AsyncSession,
    box_id: UUID,
) -> schemas.BoxContentSummaryOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    case_count, doc_count = await BoxRepository(session).count_contents(box.id)
    return schemas.BoxContentSummaryOut(
        box_id=box.id,
        box_type=box.box_type,
        case_file_count=case_count,
        administrative_document_count=doc_count,
        total_count=case_count + doc_count,
    )


async def list_box_number_history(
    session: AsyncSession,
    *,
    box_id: UUID,
    params: PageParams,
) -> Page[schemas.BoxNumberHistoryOut]:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    rows, total = await BoxRepository(session).list_number_history(
        box_id,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.BoxNumberHistoryOut.model_validate(row) for row in rows]
    return Page[schemas.BoxNumberHistoryOut].build(items, total=total, params=params)
