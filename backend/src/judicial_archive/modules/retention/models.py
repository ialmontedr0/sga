from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    DeletionStatus,
    DeletionTargetType,
    LegalHoldStatus,
    LegalHoldTargetType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class LegalHold(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "legal_holds"
    __table_args__ = (
        check_in(
            "target_type",
            LegalHoldTargetType,
            name="ck_legal_holds_target_type",
        ),
        check_in("status", LegalHoldStatus, name="ck_legal_holds_status"),
        CheckConstraint(
            "("
            "(target_type = 'BOX' AND box_id IS NOT NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'CASE_FILE' AND box_id IS NULL "
            "AND case_file_id IS NOT NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'FILE_ASSET' AND box_id IS NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NOT NULL)"
            ")",
            name="ck_legal_holds_one_target",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_legal_holds_reason_not_empty",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_legal_holds_effective_range",
        ),
        CheckConstraint(
            "status <> 'RELEASED' "
            "OR (released_at IS NOT NULL AND released_by IS NOT NULL "
            "AND release_reason IS NOT NULL "
            "AND length(btrim(release_reason)) > 0)",
            name="ck_legal_holds_release_fields",
        ),
        Index(
            "ix_legal_holds_box_active",
            "box_id",
            postgresql_where=text("status = 'ACTIVE' AND box_id IS NOT NULL"),
        ),
        Index(
            "ix_legal_holds_case_active",
            "case_file_id",
            postgresql_where=text("status = 'ACTIVE' AND case_file_id IS NOT NULL"),
        ),
        Index(
            "ix_legal_holds_file_active",
            "file_asset_id",
            postgresql_where=text("status = 'ACTIVE' AND file_asset_id IS NOT NULL"),
        ),
    )

    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    file_asset_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LegalHoldStatus.ACTIVE.value,
        server_default=LegalHoldStatus.ACTIVE.value,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    release_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class DeletionRequest(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        check_in(
            "target_type",
            DeletionTargetType,
            name="ck_deletion_requests_target_type",
        ),
        check_in("status", DeletionStatus, name="ck_deletion_requests_status"),
        CheckConstraint(
            "("
            "(target_type = 'BOX' AND box_id IS NOT NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'CASE_FILE' AND box_id IS NULL "
            "AND case_file_id IS NOT NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'FILE_ASSET' AND box_id IS NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NOT NULL)"
            ")",
            name="ck_deletion_requests_one_target",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_deletion_requests_reason_not_empty",
        ),
        CheckConstraint(
            "status NOT IN ('UNDER_REVIEW', 'APPROVED', 'SCHEDULED', "
            "'EXECUTING', 'COMPLETED', 'FAILED') "
            "OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_deletion_requests_review_fields",
        ),
        CheckConstraint(
            "status NOT IN ('APPROVED', 'SCHEDULED', 'EXECUTING', 'COMPLETED') "
            "OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)",
            name="ck_deletion_requests_approval_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' "
            "OR (rejected_at IS NOT NULL AND rejected_by IS NOT NULL "
            "AND rejection_reason IS NOT NULL "
            "AND length(btrim(rejection_reason)) > 0)",
            name="ck_deletion_requests_rejection_fields",
        ),
        CheckConstraint(
            "status <> 'CANCELLED' "
            "OR (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL "
            "AND cancellation_reason IS NOT NULL "
            "AND length(btrim(cancellation_reason)) > 0)",
            name="ck_deletion_requests_cancellation_fields",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (executed_at IS NOT NULL AND executed_by IS NOT NULL "
            "AND evidence_file_id IS NOT NULL)",
            name="ck_deletion_requests_completion_fields",
        ),
        CheckConstraint(
            "approved_by IS NULL OR approved_by <> requested_by",
            name="ck_deletion_requests_approver_separation",
        ),
        CheckConstraint(
            "executed_by IS NULL OR executed_by <> requested_by",
            name="ck_deletion_requests_executor_separation",
        ),
        CheckConstraint(
            "executed_at IS NULL OR approved_at IS NULL OR executed_at >= approved_at",
            name="ck_deletion_requests_execution_after_approval",
        ),
        CheckConstraint(
            "execution_result IS NULL OR jsonb_typeof(execution_result) = 'object'",
            name="ck_deletion_requests_result_object",
        ),
        Index("ix_deletion_requests_status", "status"),
        Index(
            "ix_deletion_requests_box_active",
            "box_id",
            postgresql_where=text(
                "box_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
        Index(
            "ix_deletion_requests_case_active",
            "case_file_id",
            postgresql_where=text(
                "case_file_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
        Index(
            "ix_deletion_requests_file_active",
            "file_asset_id",
            postgresql_where=text(
                "file_asset_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
    )

    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    file_asset_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=DeletionStatus.REQUESTED.value,
        server_default=DeletionStatus.REQUESTED.value,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
