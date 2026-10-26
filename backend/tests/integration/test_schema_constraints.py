from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import Table, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.db.base import Base

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class Baseline:
    user1: UUID
    user2: UUID
    user3: UUID
    court: UUID
    position: UUID
    box_exp: UUID
    box_admin: UUID
    box_empty: UUID
    case_file: UUID
    admin_document: UUID
    file_asset1: UUID
    file_asset2: UUID
    import_batch: UUID
    import_file: UUID
    loan1: UUID
    loan2: UUID
    inventory_session: UUID


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


async def _insert(session: AsyncSession, table_name: str, **values: Any) -> UUID:
    table = _table(table_name)
    result = await session.execute(table.insert().values(**values).returning(table.c.id))
    return cast(UUID, result.scalar_one())


async def _execute_and_commit(session: AsyncSession, statement: Any) -> None:
    await session.execute(statement)
    await session.commit()


async def _expect_integrity_error(session: AsyncSession, statement: Any) -> None:
    with pytest.raises(IntegrityError):
        await _execute_and_commit(session, statement)
    await session.rollback()


async def _expect_insert_violation(
    session: AsyncSession,
    table_name: str,
    **values: Any,
) -> None:
    table = _table(table_name)
    await _expect_integrity_error(session, table.insert().values(**values))


@pytest_asyncio.fixture
async def baseline(session_factory: async_sessionmaker[AsyncSession]) -> Baseline:
    async with session_factory() as session:
        user1 = await _insert(
            session,
            "users",
            username="user1",
            username_normalized="user1",
            display_name="User One",
            password_hash="x" * 64,
        )
        user2 = await _insert(
            session,
            "users",
            username="user2",
            username_normalized="user2",
            display_name="User Two",
            password_hash="x" * 64,
        )
        user3 = await _insert(
            session,
            "users",
            username="user3",
            username_normalized="user3",
            display_name="User Three",
            password_hash="x" * 64,
        )
        court = await _insert(
            session,
            "courts",
            code_raw="102",
            code_normalized="102",
            name="Corte de prueba",
        )
        area = await _insert(session, "areas", code="A", name="Area de prueba")
        shelf = await _insert(session, "shelves", area_id=area, code="A1")
        tray = await _insert(session, "trays", shelf_id=shelf, code="T1")
        position = await _insert(
            session,
            "positions",
            tray_id=tray,
            code="P1",
            label="Posicion 1",
        )
        box_exp = await _insert(
            session,
            "boxes",
            court_id=court,
            year=2026,
            box_type="EXPEDIENTES",
            visible_number="9001",
        )
        box_admin = await _insert(
            session,
            "boxes",
            court_id=court,
            year=2026,
            box_type="DOCUMENTOS_ADMINISTRATIVOS",
            visible_number="9002",
        )
        box_empty = await _insert(
            session,
            "boxes",
            court_id=court,
            year=2026,
            box_type="EXPEDIENTES",
            visible_number="9003",
        )
        case_file = await _insert(
            session,
            "case_files",
            court_id=court,
            box_id=box_exp,
            box_type="EXPEDIENTES",
            nuc_raw="NUC-90001",
            nuc_normalized="NUC-90001",
            year=2026,
        )
        admin_document = await _insert(
            session,
            "administrative_documents",
            box_id=box_admin,
            box_type="DOCUMENTOS_ADMINISTRATIVOS",
            title="Documento de prueba",
            document_year=2026,
        )
        file_asset1 = await _insert(
            session,
            "file_assets",
            sha256="a" * 64,
            storage_key="tests/asset-1",
            original_name="asset-1.pdf",
            mime_type="application/pdf",
            size_bytes=1,
        )
        file_asset2 = await _insert(
            session,
            "file_assets",
            sha256="b" * 64,
            storage_key="tests/asset-2",
            original_name="asset-2.pdf",
            mime_type="application/pdf",
            size_bytes=1,
        )
        import_batch = await _insert(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            created_by=user1,
        )
        import_file = await _insert(
            session,
            "import_files",
            batch_id=import_batch,
            file_asset_id=file_asset1,
            original_filename="asset-1.csv",
            source_type="CSV",
        )
        loan1 = await _insert(
            session,
            "loans",
            purpose="Prestamo de prueba 1",
            requested_by=user1,
        )
        loan2 = await _insert(
            session,
            "loans",
            purpose="Prestamo de prueba 2",
            requested_by=user1,
        )
        inventory_session = await _insert(
            session,
            "inventory_sessions",
            code="INV-BASELINE",
            scope_type="BOX",
            box_id=box_exp,
            responsible_id=user1,
        )
        await session.commit()

    return Baseline(
        user1=user1,
        user2=user2,
        user3=user3,
        court=court,
        position=position,
        box_exp=box_exp,
        box_admin=box_admin,
        box_empty=box_empty,
        case_file=case_file,
        admin_document=admin_document,
        file_asset1=file_asset1,
        file_asset2=file_asset2,
        import_batch=import_batch,
        import_file=import_file,
        loan1=loan1,
        loan2=loan2,
        inventory_session=inventory_session,
    )


@pytest.mark.asyncio
async def test_box_rejects_empty_visible_number(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="",
        )


@pytest.mark.asyncio
async def test_box_rejects_duplicate_visible_number(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="9001",
        )


@pytest.mark.asyncio
async def test_box_rejects_invalid_type(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            box_type="MIXTO",
            visible_number="9101",
        )


@pytest.mark.asyncio
async def test_box_rejects_invalid_year(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=0,
            visible_number="9102",
        )


@pytest.mark.asyncio
async def test_box_rejects_on_loan_with_current_position(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="9103",
            custody_status="ON_LOAN",
            current_position_id=baseline.position,
        )


@pytest.mark.asyncio
async def test_box_rejects_in_place_without_current_position(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="9104",
            custody_status="IN_PLACE",
        )


@pytest.mark.asyncio
async def test_two_boxes_cannot_occupy_same_position(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _insert(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="9105",
            custody_status="IN_PLACE",
            current_position_id=baseline.position,
        )
        await session.commit()

    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "boxes",
            court_id=baseline.court,
            year=2026,
            visible_number="9106",
            custody_status="IN_PLACE",
            current_position_id=baseline.position,
        )


@pytest.mark.asyncio
async def test_case_file_cannot_be_placed_in_admin_box(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "case_files",
            court_id=baseline.court,
            box_id=baseline.box_admin,
            box_type="EXPEDIENTES",
            nuc_raw="NUC-91001",
            nuc_normalized="NUC-91001",
            year=2026,
        )


@pytest.mark.asyncio
async def test_admin_document_cannot_be_placed_in_case_file_box(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "administrative_documents",
            box_id=baseline.box_exp,
            box_type="DOCUMENTOS_ADMINISTRATIVOS",
            title="Documento invalido",
            document_year=2026,
        )


@pytest.mark.asyncio
async def test_case_file_rejects_empty_nuc(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "case_files",
            court_id=baseline.court,
            nuc_raw=" ",
            nuc_normalized=" ",
            year=2026,
        )


@pytest.mark.asyncio
async def test_case_file_rejects_month_precision_without_month(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "case_files",
            court_id=baseline.court,
            nuc_raw="NUC-91002",
            nuc_normalized="NUC-91002",
            year=2026,
            entry_precision="MONTH",
            entry_year=2026,
        )


@pytest.mark.asyncio
async def test_case_file_rejects_day_precision_without_month(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "case_files",
            court_id=baseline.court,
            nuc_raw="NUC-91003",
            nuc_normalized="NUC-91003",
            year=2026,
            entry_precision="DAY",
            entry_year=2026,
            entry_day=1,
        )


@pytest.mark.asyncio
async def test_box_type_change_with_content_is_rejected(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        table = _table("boxes")
        statement = (
            table.update()
            .where(table.c.id == baseline.box_exp)
            .values(box_type="DOCUMENTOS_ADMINISTRATIVOS")
        )
        await _expect_integrity_error(session, statement)


@pytest.mark.asyncio
async def test_box_type_change_without_content_is_allowed(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        table = _table("boxes")
        await session.execute(
            table.update()
            .where(table.c.id == baseline.box_empty)
            .values(box_type="DOCUMENTOS_ADMINISTRATIVOS")
        )
        await session.commit()
        box_type = await session.scalar(
            select(table.c.box_type).where(table.c.id == baseline.box_empty)
        )

    assert box_type == "DOCUMENTOS_ADMINISTRATIVOS"


@pytest.mark.asyncio
async def test_file_attachment_rejects_two_targets(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "file_attachments",
            file_asset_id=baseline.file_asset1,
            case_file_id=baseline.case_file,
            administrative_document_id=baseline.admin_document,
            link_kind="ANNEX",
        )


@pytest.mark.asyncio
async def test_file_attachment_requires_detach_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "file_attachments",
            file_asset_id=baseline.file_asset2,
            case_file_id=baseline.case_file,
            link_kind="ANNEX",
            detached_at=func.now(),
        )


@pytest.mark.asyncio
async def test_case_file_cannot_have_two_active_primary_attachments(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _insert(
            session,
            "file_attachments",
            file_asset_id=baseline.file_asset1,
            case_file_id=baseline.case_file,
            link_kind="PRIMARY",
            is_primary=True,
        )
        await session.commit()

    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "file_attachments",
            file_asset_id=baseline.file_asset2,
            case_file_id=baseline.case_file,
            link_kind="PRIMARY",
            is_primary=True,
        )


@pytest.mark.asyncio
async def test_loan_item_rejects_two_targets(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "loan_items",
            loan_id=baseline.loan1,
            box_id=baseline.box_exp,
            case_file_id=baseline.case_file,
        )


@pytest.mark.asyncio
async def test_box_cannot_be_in_two_open_loans(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _insert(
            session,
            "loan_items",
            loan_id=baseline.loan1,
            box_id=baseline.box_exp,
        )
        await session.commit()

    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "loan_items",
            loan_id=baseline.loan2,
            box_id=baseline.box_exp,
        )


@pytest.mark.asyncio
async def test_cancelled_loan_requires_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "loans",
            purpose="Prestamo cancelado",
            requested_by=baseline.user1,
            status="CANCELLED",
            cancelled_at=func.now(),
        )


@pytest.mark.asyncio
async def test_loan_requires_different_approver(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "loans",
            purpose="Prestamo aprobado",
            requested_by=baseline.user1,
            status="APPROVED",
            approved_by=baseline.user1,
            approved_at=func.now(),
        )


@pytest.mark.asyncio
async def test_import_row_applied_without_target_is_rejected(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_rows",
            batch_id=baseline.import_batch,
            import_file_id=baseline.import_file,
            row_number=1,
            status="APPLIED",
            applied_at=func.now(),
            applied_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_import_row_rejects_two_targets(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_rows",
            batch_id=baseline.import_batch,
            import_file_id=baseline.import_file,
            row_number=2,
            target_box_id=baseline.box_exp,
            target_case_file_id=baseline.case_file,
        )


@pytest.mark.asyncio
async def test_ready_import_batch_cannot_have_errors(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            status="READY",
            created_by=baseline.user1,
            total_rows=1,
            error_rows=1,
        )


@pytest.mark.asyncio
async def test_failed_import_batch_requires_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            status="FAILED",
            created_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_import_batch_requires_different_approver_without_exception(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            created_by=baseline.user1,
            approved_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_import_batch_idempotency_key_is_unique_per_creator(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _insert(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            created_by=baseline.user1,
            idempotency_key="import-1",
        )
        await session.commit()

    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "import_batches",
            import_kind="INVENTORY_TABLE",
            source_type="CSV",
            created_by=baseline.user1,
            idempotency_key="import-1",
        )


@pytest.mark.asyncio
async def test_legal_hold_rejects_two_targets(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "legal_holds",
            target_type="BOX",
            box_id=baseline.box_exp,
            case_file_id=baseline.case_file,
            reason="Retencion de prueba",
            created_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_legal_hold_requires_target(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "legal_holds",
            target_type="BOX",
            reason="Retencion sin objetivo",
            created_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_released_legal_hold_requires_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "legal_holds",
            target_type="BOX",
            box_id=baseline.box_exp,
            reason="Retencion liberada",
            created_by=baseline.user1,
            status="RELEASED",
            released_at=func.now(),
            released_by=baseline.user2,
        )


@pytest.mark.asyncio
async def test_deletion_request_rejects_two_targets(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "deletion_requests",
            target_type="BOX",
            box_id=baseline.box_exp,
            case_file_id=baseline.case_file,
            reason="Borrado de prueba",
            requested_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_deletion_request_requires_different_approver(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "deletion_requests",
            target_type="BOX",
            box_id=baseline.box_exp,
            reason="Solicitud de borrado",
            requested_by=baseline.user1,
            approved_by=baseline.user1,
        )


@pytest.mark.asyncio
async def test_completed_deletion_request_requires_evidence(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "deletion_requests",
            target_type="BOX",
            box_id=baseline.box_exp,
            reason="Borrado completado",
            requested_by=baseline.user1,
            status="COMPLETED",
            reviewed_at=func.now(),
            reviewed_by=baseline.user2,
            approved_at=func.now(),
            approved_by=baseline.user2,
            executed_at=func.now(),
            executed_by=baseline.user3,
        )


@pytest.mark.asyncio
async def test_rejected_deletion_request_requires_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "deletion_requests",
            target_type="BOX",
            box_id=baseline.box_exp,
            reason="Borrado rechazado",
            requested_by=baseline.user1,
            status="REJECTED",
            rejected_at=func.now(),
            rejected_by=baseline.user2,
        )


@pytest.mark.asyncio
async def test_cancelled_deletion_request_requires_reason(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "deletion_requests",
            target_type="BOX",
            box_id=baseline.box_exp,
            reason="Borrado cancelado",
            requested_by=baseline.user1,
            status="CANCELLED",
            cancelled_at=func.now(),
            cancelled_by=baseline.user2,
        )


@pytest.mark.asyncio
async def test_resolved_inventory_finding_requires_resolution(
    baseline: Baseline,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _expect_insert_violation(
            session,
            "inventory_findings",
            session_id=baseline.inventory_session,
            finding_type="MISSING_BOX",
            finding_status="RESOLVED",
            resolved_at=func.now(),
            resolved_by=baseline.user1,
        )
