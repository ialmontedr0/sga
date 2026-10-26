from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    ImportFileStatus,
    ImportKind,
    ImportRowStatus,
    ImportSourceType,
    ImportStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        check_in("import_kind", ImportKind, name="ck_import_batches_kind"),
        check_in("source_type", ImportSourceType, name="ck_import_batches_source"),
        check_in("status", ImportStatus, name="ck_import_batches_status"),
        CheckConstraint(
            "total_files >= 0 AND processed_files >= 0 "
            "AND total_rows >= 0 AND valid_rows >= 0 "
            "AND warning_rows >= 0 AND error_rows >= 0",
            name="ck_import_batches_non_negative_counts",
        ),
        CheckConstraint(
            "processed_files <= total_files",
            name="ck_import_batches_processed_files",
        ),
        CheckConstraint(
            "valid_rows + warning_rows + error_rows <= total_rows",
            name="ck_import_batches_row_counts",
        ),
        CheckConstraint(
            "status NOT IN ('READY', 'APPLYING', 'APPLIED') OR error_rows = 0",
            name="ck_import_batches_ready_without_errors",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)",
            name="ck_import_batches_applied_fields",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR ("
            "failure_reason IS NOT NULL "
            "AND length(btrim(failure_reason)) > 0)",
            name="ck_import_batches_failure_reason",
        ),
        CheckConstraint(
            "approved_by IS NULL OR created_by IS NULL "
            "OR approved_by <> created_by "
            "OR (approval_exception_reason IS NOT NULL "
            "AND length(btrim(approval_exception_reason)) > 0)",
            name="ck_import_batches_separation",
        ),
        CheckConstraint(
            "idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0",
            name="ck_import_batches_idempotency_key",
        ),
        Index("ix_import_batches_status", "status"),
        Index("ix_import_batches_created_at", "created_at"),
        Index(
            "uq_import_batches_idempotency",
            "created_by",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL AND created_by IS NOT NULL"),
        ),
    )

    import_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=ImportStatus.DRAFT.value,
        server_default=ImportStatus.DRAFT.value,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_files: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    processed_files: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    total_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    valid_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    warning_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    applied_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approval_exception_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ImportFile(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "import_files"
    __table_args__ = (
        UniqueConstraint("id", "batch_id", name="uq_import_files_id_batch"),
        UniqueConstraint(
            "batch_id",
            "file_asset_id",
            name="uq_import_files_batch_asset",
        ),
        check_in("source_type", ImportSourceType, name="ck_import_files_source"),
        check_in("status", ImportFileStatus, name="ck_import_files_status"),
        CheckConstraint(
            "rows_extracted >= 0",
            name="ck_import_files_rows_extracted",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_import_files_page_count",
        ),
        CheckConstraint(
            "error IS NULL OR jsonb_typeof(error) = 'object'",
            name="ck_import_files_error_object",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR error IS NOT NULL",
            name="ck_import_files_failed_error",
        ),
        CheckConstraint(
            "status <> 'EXTRACTED' OR extracted_at IS NOT NULL",
            name="ck_import_files_extracted_at",
        ),
        Index("ix_import_files_batch_id", "batch_id"),
        Index("ix_import_files_status", "status"),
    )

    batch_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=ImportFileStatus.PENDING.value,
        server_default=ImportFileStatus.PENDING.value,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_extracted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class ImportRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_file_id", "batch_id"],
            ["import_files.id", "import_files.batch_id"],
            name="fk_import_rows_file_batch",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("status", ImportRowStatus, name="ck_import_rows_status"),
        CheckConstraint(
            "row_number > 0",
            name="ck_import_rows_row_number",
        ),
        CheckConstraint(
            "raw_data IS NULL OR jsonb_typeof(raw_data) = 'object'",
            name="ck_import_rows_raw_object",
        ),
        CheckConstraint(
            "normalized_data IS NULL OR jsonb_typeof(normalized_data) = 'object'",
            name="ck_import_rows_normalized_object",
        ),
        CheckConstraint(
            "errors IS NULL OR jsonb_typeof(errors) = 'array'",
            name="ck_import_rows_errors_array",
        ),
        CheckConstraint(
            "warnings IS NULL OR jsonb_typeof(warnings) = 'array'",
            name="ck_import_rows_warnings_array",
        ),
        CheckConstraint(
            "("
            "(target_box_id IS NOT NULL)::int "
            "+ (target_case_file_id IS NOT NULL)::int "
            "+ (target_administrative_document_id IS NOT NULL)::int"
            ") <= 1",
            name="ck_import_rows_at_most_one_target",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR ("
            "(target_box_id IS NOT NULL)::int "
            "+ (target_case_file_id IS NOT NULL)::int "
            "+ (target_administrative_document_id IS NOT NULL)::int"
            ") = 1",
            name="ck_import_rows_applied_target",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)",
            name="ck_import_rows_applied_fields",
        ),
        CheckConstraint(
            "status <> 'ERROR' OR errors IS NOT NULL",
            name="ck_import_rows_error_details",
        ),
        Index("ix_import_rows_batch_id", "batch_id"),
        Index("ix_import_rows_import_file_id", "import_file_id"),
        Index("ix_import_rows_status", "status"),
        UniqueConstraint(
            "import_file_id",
            "row_number",
            name="uq_import_rows_file_row",
        ),
    )

    batch_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    import_file_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ImportRowStatus.PENDING.value,
        server_default=ImportRowStatus.PENDING.value,
    )
    errors: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    target_box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_administrative_document_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("administrative_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
