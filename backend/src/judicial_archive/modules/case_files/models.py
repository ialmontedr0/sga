from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxType,
    Confidentiality,
    IdentifierKind,
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
    partial_date_checks,
)


class CaseFile(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "case_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["box_id", "box_type"],
            ["boxes.id", "boxes.box_type"],
            name="fk_case_files_box_type",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("box_type", BoxType, name="ck_case_files_box_type"),
        check_in("lifecycle_status", LifecycleStatus, name="ck_case_files_lifecycle"),
        check_in(
            "verification_status",
            VerificationStatus,
            name="ck_case_files_verification",
        ),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_case_files_confidentiality",
        ),
        CheckConstraint(
            "box_type = 'EXPEDIENTES'",
            name="ck_case_files_box_type_expedientes",
        ),
        CheckConstraint(
            "box_id IS NULL OR box_type = 'EXPEDIENTES'",
            name="ck_case_files_box_type_consistency",
        ),
        CheckConstraint(
            "length(btrim(nuc_raw)) > 0",
            name="ck_case_files_nuc_raw_not_empty",
        ),
        CheckConstraint(
            "length(btrim(nuc_normalized)) > 0",
            name="ck_case_files_nuc_normalized_not_empty",
        ),
        CheckConstraint(
            "year BETWEEN 1 AND 9999",
            name="ck_case_files_year_range",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_case_files_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_case_files_voided_at",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_case_files_deleted_actor",
        ),
        *partial_date_checks("case_files", "entry"),
        *partial_date_checks("case_files", "sentence"),
        Index("ix_case_files_court_nuc", "court_id", "nuc_normalized"),
        Index("ix_case_files_nuc_suffix5", "nuc_suffix5"),
        Index("ix_case_files_box_id", "box_id"),
        Index("ix_case_files_year", "year"),
        Index("ix_case_files_lifecycle", "lifecycle_status"),
        Index("ix_case_files_verification", "verification_status"),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.EXPEDIENTES.value,
        server_default=BoxType.EXPEDIENTES.value,
    )
    nuc_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    nuc_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    nuc_suffix5: Mapped[str] = mapped_column(
        String(5),
        Computed("right(nuc_normalized, 5)", persisted=True),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'UNKNOWN'")
    )
    sentence_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'UNKNOWN'")
    )
    resolution_type_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("resolution_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resolution_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    judge_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    court_name_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
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


class CaseFileIdentifierHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_file_identifier_history"
    __table_args__ = (
        check_in("identifier_kind", IdentifierKind, name="ck_case_identifier_kind"),
        CheckConstraint(
            "length(btrim(value_raw)) > 0",
            name="ck_case_identifier_raw_not_empty",
        ),
        CheckConstraint(
            "length(btrim(value_normalized)) > 0",
            name="ck_case_identifier_normalized_not_empty",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_case_identifier_reason_not_empty",
        ),
        Index(
            "ix_case_file_identifier_case",
            "case_file_id",
            "changed_at",
        ),
        Index(
            "ix_case_file_identifier_lookup",
            "identifier_kind",
            "value_normalized",
        ),
    )

    case_file_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    value_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    value_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class Person(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "persons"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_persons_display_name_not_empty",
        ),
        CheckConstraint(
            "length(btrim(normalized_name)) > 0",
            name="ck_persons_normalized_name_not_empty",
        ),
        CheckConstraint(
            "aliases IS NULL OR jsonb_typeof(aliases) = 'array'",
            name="ck_persons_aliases_array",
        ),
        CheckConstraint(
            "birth_year IS NULL OR birth_year BETWEEN 1 AND 9999",
            name="ck_persons_birth_year_range",
        ),
        CheckConstraint(
            "birth_month IS NULL OR birth_month BETWEEN 1 AND 12",
            name="ck_persons_birth_month_range",
        ),
        CheckConstraint(
            "birth_day IS NULL OR birth_day BETWEEN 1 AND 31",
            name="ck_persons_birth_day_range",
        ),
        CheckConstraint(
            "birth_day IS NULL OR birth_month IS NOT NULL",
            name="ck_persons_birth_day_requires_month",
        ),
        CheckConstraint(
            "birth_month IS NULL OR birth_year IS NOT NULL",
            name="ck_persons_birth_month_requires_year",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_persons_deleted_actor",
        ),
        Index("ix_persons_normalized_name", "normalized_name"),
        Index("ix_persons_identification", "identification_number"),
    )

    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)
    aliases: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    identification_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    identification_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class CaseParty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_parties"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(notes)) > 0 OR notes IS NULL",
            name="ck_case_parties_notes_not_blank",
        ),
        Index("ix_case_parties_case_file_id", "case_file_id"),
        Index("ix_case_parties_person_id", "person_id"),
    )

    case_file_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        nullable=False,
    )
    party_role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("party_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
