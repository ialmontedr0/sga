from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import BoxLifecycleStatus, BoxType, LifecycleStatus
from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.administrative_documents import schemas
from judicial_archive.modules.administrative_documents.models import AdministrativeDocument
from judicial_archive.modules.administrative_documents.repositories import (
    AdministrativeDocumentRepository,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.case_files.validators import validate_partial_date
from judicial_archive.modules.users.models import User


def _snapshot(document: AdministrativeDocument) -> dict[str, object]:
    return {
        "box_id": str(document.box_id),
        "title": document.title,
        "document_type": document.document_type,
        "document_year": document.document_year,
        "document_month": document.document_month,
        "document_day": document.document_day,
        "confidentiality": document.confidentiality,
        "lifecycle_status": document.lifecycle_status,
        "version": document.version,
    }


async def _active_admin_box(
    session: AsyncSession,
    box_id: UUID,
    *,
    lock: bool = True,
) -> Box:
    repo = BoxRepository(session)
    box = await repo.get_for_update(box_id) if lock else await repo.get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError("La caja no esta activa.", details={"reason": "box_not_active"})
    if box.box_type != BoxType.DOCUMENTOS_ADMINISTRATIVOS.value:
        raise InvalidParameterError(
            "Un documento administrativo solo puede pertenecer a una caja administrativa.",
            details={"reason": "box_type_mismatch"},
        )
    return box


async def prepare_administrative_document(
    session: AsyncSession,
    *,
    actor: User,
    box: Box,
    body: schemas.AdministrativeDocumentInlineCreate,
) -> tuple[AdministrativeDocument, list[str]]:
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError("La caja no esta activa.", details={"reason": "box_not_active"})
    if box.box_type != BoxType.DOCUMENTOS_ADMINISTRATIVOS.value:
        raise InvalidParameterError(
            "La caja no admite documentos administrativos.",
            details={"reason": "box_type_mismatch"},
        )
    validate_partial_date(
        precision="DAY" if body.document_day else ("MONTH" if body.document_month else "YEAR"),
        year=body.document_year,
        month=body.document_month,
        day=body.document_day,
        field="document",
    )
    repo = AdministrativeDocumentRepository(session)
    duplicate = await repo.find_duplicate(
        box_id=box.id,
        title=body.title,
        document_year=body.document_year,
    )
    if duplicate is not None:
        raise ConflictError(
            "Ya existe un documento con el mismo titulo y anio en la caja.",
            details={
                "reason": "duplicate_administrative_document",
                "document_id": str(duplicate.id),
            },
        )
    document = AdministrativeDocument(
        box_id=box.id,
        box_type=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
        title=" ".join(body.title.strip().split()),
        document_type=clean_optional_text(body.document_type, max_length=80),
        document_year=body.document_year,
        document_month=body.document_month,
        document_day=body.document_day,
        description=clean_optional_text(body.description, max_length=1000),
        confidentiality=body.confidentiality,
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        source=clean_optional_text(body.source, max_length=32),
        notes=clean_optional_text(body.notes, max_length=2000),
        created_by=actor.id,
    )
    session.add(document)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "No se pudo crear el documento administrativo.",
            details={"reason": "administrative_document_integrity_conflict"},
        ) from exc
    return document, []


async def create_administrative_document(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.AdministrativeDocumentCreate,
) -> schemas.AdministrativeDocumentOut:
    try:
        box = await _active_admin_box(session, body.box_id)
        document, warnings = await prepare_administrative_document(
            session,
            actor=actor,
            box=box,
            body=body,
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="administrative_document.created",
            entity_type="administrative_document",
            entity_id=document.id,
            after=_snapshot(document),
            metadata={"warnings": warnings},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(document)
    return schemas.AdministrativeDocumentOut.model_validate(document)


async def list_administrative_document_duplicates(
    session: AsyncSession,
    *,
    box_id: UUID,
    title: str,
    document_year: int,
) -> list[schemas.DuplicateAdministrativeDocumentOut]:
    duplicate = await AdministrativeDocumentRepository(session).find_duplicate(
        box_id=box_id,
        title=title,
        document_year=document_year,
    )
    if duplicate is None:
        return []
    return [
        schemas.DuplicateAdministrativeDocumentOut(
            id=duplicate.id,
            box_id=duplicate.box_id,
            title=duplicate.title,
            document_year=duplicate.document_year,
            match_type="EXACT",
        )
    ]


async def list_administrative_documents(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    box_id: UUID | None,
    document_year: int | None,
    lifecycle_status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.AdministrativeDocumentOut]:
    rows, total = await AdministrativeDocumentRepository(session).list_items(
        q=q,
        box_id=box_id,
        document_year=document_year,
        lifecycle_status=lifecycle_status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.AdministrativeDocumentOut.model_validate(row) for row in rows]
    return Page[schemas.AdministrativeDocumentOut].build(
        items,
        total=total,
        params=params,
    )


async def get_administrative_document(
    session: AsyncSession,
    document_id: UUID,
) -> schemas.AdministrativeDocumentOut:
    document = await AdministrativeDocumentRepository(session).get(document_id)
    if document is None or document.deleted_at is not None:
        raise NotFoundError("Documento administrativo no encontrado.")
    return schemas.AdministrativeDocumentOut.model_validate(document)


async def update_administrative_document(
    request: Request,
    session: AsyncSession,
    actor: User,
    document_id: UUID,
    body: schemas.AdministrativeDocumentUpdate,
) -> schemas.AdministrativeDocumentOut:
    repo = AdministrativeDocumentRepository(session)
    try:
        document = await repo.get_for_update(document_id)
        if document is None:
            raise NotFoundError("Documento administrativo no encontrado.")
        if document.version != body.expected_version:
            raise ConflictError(
                "El documento fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": document.version},
            )
        if document.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un documento anulado no puede modificarse.",
                details={"reason": "administrative_document_voided"},
            )

        before = _snapshot(document)
        changes = body.model_dump(exclude_unset=True)
        changes.pop("expected_version", None)

        if "title" in changes:
            title = changes["title"]
            if title is None:
                raise InvalidParameterError("El titulo no puede estar vacio.")
            document.title = " ".join(title.strip().split())
        if "document_year" in changes:
            document_year = changes["document_year"]
            if document_year is None:
                raise InvalidParameterError("El anio del documento es obligatorio.")
            document.document_year = document_year
        for field in ("document_month", "document_day"):
            if field in changes:
                setattr(document, field, changes[field])
        for field, max_length in (
            ("document_type", 80),
            ("description", 1000),
            ("source", 32),
            ("notes", 2000),
        ):
            if field in changes:
                setattr(
                    document,
                    field,
                    clean_optional_text(changes[field], max_length=max_length),
                )
        if "confidentiality" in changes and changes["confidentiality"] is not None:
            document.confidentiality = changes["confidentiality"]

        validate_partial_date(
            precision=(
                "DAY" if document.document_day else ("MONTH" if document.document_month else "YEAR")
            ),
            year=document.document_year,
            month=document.document_month,
            day=document.document_day,
            field="document",
        )

        if "title" in changes or "document_year" in changes:
            duplicate = await repo.find_duplicate(
                box_id=document.box_id,
                title=document.title,
                document_year=document.document_year,
                exclude_id=document.id,
            )
            if duplicate is not None:
                raise ConflictError(
                    "Ya existe un documento con el mismo titulo y anio en la caja.",
                    details={
                        "reason": "duplicate_administrative_document",
                        "document_id": str(duplicate.id),
                    },
                )

        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="administrative_document.updated",
            entity_type="administrative_document",
            entity_id=document.id,
            before=before,
            after=_snapshot(document),
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "El documento fue modificado por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(document)
    return schemas.AdministrativeDocumentOut.model_validate(document)


async def set_administrative_document_lifecycle(
    request: Request,
    session: AsyncSession,
    actor: User,
    document_id: UUID,
    *,
    target: str,
    body: schemas.AdministrativeDocumentLifecycleRequest,
) -> schemas.AdministrativeDocumentOut:
    if target not in {
        LifecycleStatus.ARCHIVED.value,
        LifecycleStatus.VOIDED.value,
    }:
        raise InvalidParameterError("Transicion de documento no permitida.")
    repo = AdministrativeDocumentRepository(session)
    try:
        document = await repo.get_for_update(document_id)
        if document is None:
            raise NotFoundError("Documento administrativo no encontrado.")
        if document.version != body.expected_version:
            raise ConflictError(
                "El documento fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": document.version},
            )
        before = _snapshot(document)
        now = datetime.now(UTC)
        if target == LifecycleStatus.ARCHIVED.value:
            if document.lifecycle_status != LifecycleStatus.ACTIVE.value:
                raise ConflictError(
                    "Solo un documento activo puede archivarse.",
                    details={"reason": "administrative_document_not_active"},
                )
            document.lifecycle_status = target
            document.archived_at = now
            document.archived_by = actor.id
            document.archive_reason = body.reason.strip()
            action = "administrative_document.archived"
        else:
            if document.lifecycle_status == LifecycleStatus.VOIDED.value:
                raise ConflictError("El documento ya esta anulado.")
            document.lifecycle_status = target
            document.voided_at = now
            document.voided_by = actor.id
            document.void_reason = body.reason.strip()
            action = "administrative_document.voided"
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action=action,
            entity_type="administrative_document",
            entity_id=document.id,
            before=before,
            after=_snapshot(document),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(document)
    return schemas.AdministrativeDocumentOut.model_validate(document)


async def soft_delete_administrative_document(
    request: Request,
    session: AsyncSession,
    actor: User,
    document_id: UUID,
    body: schemas.AdministrativeDocumentDeleteRequest,
) -> None:
    repo = AdministrativeDocumentRepository(session)
    try:
        document = await repo.get_for_update(document_id)
        if document is None:
            raise NotFoundError("Documento administrativo no encontrado.")
        if document.version != body.expected_version:
            raise ConflictError(
                "El documento fue modificado por otro usuario.",
                details={"reason": "stale_version", "current_version": document.version},
            )
        if document.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un documento anulado no puede darse de baja.",
                details={"reason": "administrative_document_voided"},
            )
        before = _snapshot(document)
        document.deleted_at = datetime.now(UTC)
        document.deleted_by = actor.id
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="administrative_document.deleted",
            entity_type="administrative_document",
            entity_id=document.id,
            before=before,
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
