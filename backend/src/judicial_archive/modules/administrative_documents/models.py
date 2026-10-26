from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxType,
    Confidentiality,
    LifecycleStatus,
    VerificationStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class AdministrativeDocument(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "administrative_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["box_id", "box_type"],
            ["boxes.id", "boxes.box_type"],
            name="fk_administrative_documents_box_type",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("box_type", BoxType, name="ck_admin_documents_box_type"),
        check_in(
            "lifecycle_status",
            LifecycleStatus,
            name="ck_admin_documents_lifecycle",
        ),
        check_in(
            "verification_status",
            VerificationStatus,
            name="ck_admin_documents_verification",
        ),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_admin_documents_confidentiality",
        ),
        CheckConstraint(
            "box_type = 'DOCUMENTOS_ADMINISTRATIVOS'",
            name="ck_admin_documents_box_type_admin",
        ),
        CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_admin_documents_title_not_empty",
        ),
        CheckConstraint(
            "document_year BETWEEN 1 AND 9999",
            name="ck_admin_documents_year_range",
        ),
        CheckConstraint(
            "document_month IS NULL OR document_month BETWEEN 1 AND 12",
            name="ck_admin_documents_month_range",
        ),
        CheckConstraint(
            "document_day IS NULL OR document_day BETWEEN 1 AND 31",
            name="ck_admin_documents_day_range",
        ),
        CheckConstraint(
            "document_day IS NULL OR document_month IS NOT NULL",
            name="ck_admin_documents_day_requires_month",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_admin_documents_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_admin_documents_voided_at",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_admin_documents_deleted_actor",
        ),
        Index("ix_admin_documents_box_id", "box_id"),
        Index("ix_admin_documents_year", "document_year"),
        Index("ix_admin_documents_lifecycle", "lifecycle_status"),
    )

    box_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
        server_default=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    document_year: Mapped[int] = mapped_column(Integer, nullable=False)
    document_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=VerificationStatus.PENDING.value,
        server_default=VerificationStatus.PENDING.value,
    )
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Confidentiality.INTERNAL.value,
        server_default=Confidentiality.INTERNAL.value,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LifecycleStatus.ACTIVE.value,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
