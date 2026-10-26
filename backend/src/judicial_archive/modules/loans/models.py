from __future__ import annotations

from datetime import datetime
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
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import LoanStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Loan(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        check_in("status", LoanStatus, name="ck_loans_status"),
        CheckConstraint(
            "length(btrim(purpose)) > 0",
            name="ck_loans_purpose_not_empty",
        ),
        CheckConstraint(
            "status NOT IN ('APPROVED', 'DELIVERED', 'RETURNED') "
            "OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)",
            name="ck_loans_approval_fields",
        ),
        CheckConstraint(
            "status NOT IN ('DELIVERED', 'RETURNED') "
            "OR (delivered_at IS NOT NULL AND delivered_by IS NOT NULL)",
            name="ck_loans_delivery_fields",
        ),
        CheckConstraint(
            "status <> 'RETURNED' OR (returned_at IS NOT NULL AND returned_by IS NOT NULL)",
            name="ck_loans_return_fields",
        ),
        CheckConstraint(
            "status <> 'CANCELLED' "
            "OR (cancelled_at IS NOT NULL "
            "AND cancellation_reason IS NOT NULL "
            "AND length(btrim(cancellation_reason)) > 0)",
            name="ck_loans_cancellation_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' "
            "OR (rejected_at IS NOT NULL "
            "AND rejection_reason IS NOT NULL "
            "AND length(btrim(rejection_reason)) > 0)",
            name="ck_loans_rejection_fields",
        ),
        CheckConstraint(
            "approved_by IS NULL OR requested_by IS NULL "
            "OR approved_by <> requested_by "
            "OR (approval_exception_reason IS NOT NULL "
            "AND length(btrim(approval_exception_reason)) > 0)",
            name="ck_loans_approval_separation",
        ),
        CheckConstraint(
            "due_at IS NULL OR delivered_at IS NULL OR due_at >= delivered_at",
            name="ck_loans_due_after_delivery",
        ),
        CheckConstraint(
            "returned_at IS NULL OR delivered_at IS NULL OR returned_at >= delivered_at",
            name="ck_loans_return_after_delivery",
        ),
        CheckConstraint(
            "approved_at IS NULL OR approved_at >= requested_at",
            name="ck_loans_approval_after_request",
        ),
        Index("ix_loans_status", "status"),
        Index("ix_loans_requested_at", "requested_at"),
        Index("ix_loans_due_at", "due_at"),
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LoanStatus.REQUESTED.value,
        server_default=LoanStatus.REQUESTED.value,
    )
    purpose: Mapped[str] = mapped_column(String(1000), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approval_exception_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class LoanItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "loan_items"
    __table_args__ = (
        CheckConstraint(
            "("
            "(box_id IS NOT NULL AND case_file_id IS NULL)"
            " OR (box_id IS NULL AND case_file_id IS NOT NULL)"
            ")",
            name="ck_loan_items_one_target",
        ),
        CheckConstraint(
            "released_at IS NULL OR ("
            "release_reason IS NOT NULL "
            "AND length(btrim(release_reason)) > 0)",
            name="ck_loan_items_release_reason",
        ),
        CheckConstraint(
            "released_at IS NULL OR released_at >= created_at",
            name="ck_loan_items_release_after_creation",
        ),
        Index("ix_loan_items_loan_id", "loan_id"),
        Index(
            "uq_loan_items_open_box",
            "box_id",
            unique=True,
            postgresql_where=text("released_at IS NULL AND box_id IS NOT NULL"),
        ),
        Index(
            "uq_loan_items_open_case",
            "case_file_id",
            unique=True,
            postgresql_where=text("released_at IS NULL AND case_file_id IS NOT NULL"),
        ),
    )

    loan_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
