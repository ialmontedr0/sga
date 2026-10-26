from __future__ import annotations

from sqlalchemy import CheckConstraint, Enum, Index, UniqueConstraint

import judicial_archive.db.base
import judicial_archive.models

EXPECTED_TABLES = {
    "administrative_documents",
    "areas",
    "audit_events",
    "box_labels",
    "box_movements",
    "box_number_history",
    "boxes",
    "case_file_identifier_history",
    "case_files",
    "case_parties",
    "courts",
    "deletion_requests",
    "file_assets",
    "file_attachments",
    "identifier_format_profiles",
    "import_batches",
    "import_files",
    "import_rows",
    "inventory_findings",
    "inventory_sessions",
    "legal_holds",
    "loan_items",
    "loans",
    "numbering_policies",
    "ocr_results",
    "party_roles",
    "permissions",
    "persons",
    "position_blocks",
    "positions",
    "resolution_types",
    "retention_policies",
    "role_permissions",
    "roles",
    "shelves",
    "system_settings",
    "task_jobs",
    "trays",
    "user_roles",
    "user_sessions",
    "users",
}

EXPECTED_PARTIAL_INDEXES = {
    "uq_boxes_current_position_occupied",
    "uq_identifier_format_profiles_active",
    "uq_file_attachments_case_primary",
    "uq_file_attachments_admin_primary",
    "uq_loan_items_open_box",
    "uq_loan_items_open_case",
    "uq_import_batches_idempotency",
    "uq_task_jobs_idempotency",
    "uq_numbering_policies_active_global",
    "uq_numbering_policies_active_court",
    "uq_numbering_policies_active_box_type",
    "uq_numbering_policies_active_year",
}


def test_tables_exactas() -> None:
    assert set(judicial_archive.db.base.Base.metadata.tables) == EXPECTED_TABLES


def test_todas_las_tablas_tienen_pk() -> None:
    for table in judicial_archive.db.base.Base.metadata.tables.values():
        assert table.primary_key.columns, table.name


def test_checks_tienen_nombre_completo() -> None:
    for table in judicial_archive.db.base.Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint):
                assert constraint.name, table.name
                assert constraint.name.startswith("ck_"), constraint.name  # type: ignore
                assert "ck_ck_" not in constraint.name, constraint.name  # type: ignore


def test_no_hay_enum_nativo() -> None:
    for table in judicial_archive.db.base.Base.metadata.tables.values():
        for column in table.columns:
            assert not isinstance(column.type, Enum), f"{table.name}.{column.name}"


def test_fk_apuntan_a_tablas_registradas() -> None:
    for table in judicial_archive.db.base.Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.column.table.name in EXPECTED_TABLES


def test_indices_parciales_presentes() -> None:
    names: set[str] = set()
    for table in judicial_archive.db.base.Base.metadata.tables.values():
        for index in table.indexes:
            if index.dialect_options["postgresql"].get("where") is not None:
                assert isinstance(index, Index)
                names.add(index.name or "")
    assert names >= EXPECTED_PARTIAL_INDEXES


def test_unique_compuesta_de_caja() -> None:
    table = judicial_archive.db.base.Base.metadata.tables["boxes"]
    names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_boxes_id_box_type" in names
