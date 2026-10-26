from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import FileLinkKind, FileStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class FileAsset(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "file_assets"
    __table_args__ = (
        check_in("status", FileStatus, name="ck_file_assets_status"),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_file_assets_sha256_format",
        ),
        CheckConstraint(
            "length(btrim(storage_key)) > 0",
            name="ck_file_assets_storage_key_not_empty",
        ),
        CheckConstraint(
            "length(btrim(original_name)) > 0",
            name="ck_file_assets_original_name_not_empty",
        ),
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_file_assets_size_non_negative",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_file_assets_page_count",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_file_assets_metadata_object",
        ),
        CheckConstraint(
            "status <> 'DELETED' OR deleted_at IS NOT NULL",
            name="ck_file_assets_deleted_status",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_file_assets_deleted_actor",
        ),
        Index("ix_file_assets_sha256", "sha256"),
        Index("ix_file_assets_status", "status"),
    )

    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=FileStatus.PENDING.value,
        server_default=FileStatus.PENDING.value,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FileAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "file_attachments"
    __table_args__ = (
        check_in("link_kind", FileLinkKind, name="ck_file_attachments_link_kind"),
        CheckConstraint(
            "("
            "(case_file_id IS NOT NULL AND administrative_document_id IS NULL)"
            " OR (case_file_id IS NULL AND administrative_document_id IS NOT NULL)"
            ")",
            name="ck_file_attachments_one_target",
        ),
        CheckConstraint(
            "detached_at IS NULL OR ("
            "detached_reason IS NOT NULL "
            "AND length(btrim(detached_reason)) > 0)",
            name="ck_file_attachments_detached_reason",
        ),
        CheckConstraint(
            "is_primary = false OR detached_at IS NULL",
            name="ck_file_attachments_primary_not_detached",
        ),
        Index("ix_file_attachments_file_asset", "file_asset_id"),
        Index("ix_file_attachments_case_file", "case_file_id"),
        Index("ix_file_attachments_admin_document", "administrative_document_id"),
        Index(
            "uq_file_attachments_case_primary",
            "case_file_id",
            unique=True,
            postgresql_where=text(
                "is_primary AND detached_at IS NULL AND case_file_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_file_attachments_admin_primary",
            "administrative_document_id",
            unique=True,
            postgresql_where=text(
                "is_primary AND detached_at IS NULL AND administrative_document_id IS NOT NULL"
            ),
        ),
    )

    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    administrative_document_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("administrative_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    link_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detached_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detached_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
