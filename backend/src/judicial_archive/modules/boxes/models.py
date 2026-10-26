from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    BoxType,
    Confidentiality,
    CustodyStatus,
    LocationPrecision,
    MovementStatus,
    MovementType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Box(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "boxes"
    __table_args__ = (
        UniqueConstraint("visible_number", name="uq_boxes_visible_number"),
        UniqueConstraint("id", "box_type", name="uq_boxes_id_box_type"),
        check_in("box_type", BoxType, name="ck_boxes_box_type"),
        check_in(
            "lifecycle_status",
            BoxLifecycleStatus,
            name="ck_boxes_lifecycle_status",
        ),
        check_in("custody_status", CustodyStatus, name="ck_boxes_custody_status"),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_boxes_confidentiality",
        ),
        check_in(
            "location_precision",
            LocationPrecision,
            name="ck_boxes_location_precision",
        ),
        CheckConstraint(
            "year BETWEEN 1 AND 9999",
            name="ck_boxes_year_range",
        ),
        CheckConstraint(
            "length(btrim(visible_number)) > 0",
            name="ck_boxes_visible_number_not_empty",
        ),
        CheckConstraint(
            "("
            "(custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NOT NULL)"
            " OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NULL)"
            ")",
            name="ck_boxes_custody_position",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_boxes_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_boxes_voided_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'DESTROYED' OR destroyed_at IS NOT NULL",
            name="ck_boxes_destroyed_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'DESTROYED' OR current_position_id IS NULL",
            name="ck_boxes_destroyed_without_position",
        ),
        Index(
            "ix_boxes_court_year_type",
            "court_id",
            "year",
            "box_type",
        ),
        Index("ix_boxes_lifecycle_status", "lifecycle_status"),
        Index("ix_boxes_custody_status", "custody_status"),
        Index(
            "uq_boxes_current_position_occupied",
            "current_position_id",
            unique=True,
            postgresql_where=text(
                "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
                "AND current_position_id IS NOT NULL"
            ),
        ),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.EXPEDIENTES.value,
        server_default=BoxType.EXPEDIENTES.value,
    )
    visible_number: Mapped[str] = mapped_column(String(32), nullable=False)
    numbering_policy_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("numbering_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Confidentiality.INTERNAL.value,
        server_default=Confidentiality.INTERNAL.value,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=BoxLifecycleStatus.ACTIVE.value,
        server_default=BoxLifecycleStatus.ACTIVE.value,
    )
    custody_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=CustodyStatus.UNKNOWN.value,
        server_default=CustodyStatus.UNKNOWN.value,
    )
    current_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    location_precision: Mapped[str] = mapped_column(
        String(16),
        Computed(
            "CASE "
            "WHEN current_position_id IS NULL THEN 'UNKNOWN' "
            "WHEN custody_status = 'IN_PLACE' THEN 'CONFIRMED' "
            "ELSE 'PENDING' "
            "END",
            persisted=True,
        ),
        nullable=False,
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
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    destroyed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    destruction_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class BoxNumberHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "box_number_history"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(new_number)) > 0",
            name="ck_box_number_history_new_number_not_empty",
        ),
        CheckConstraint(
            "previous_number IS NULL OR length(btrim(previous_number)) > 0",
            name="ck_box_number_history_previous_number_not_empty",
        ),
        CheckConstraint(
            "previous_number IS NULL OR previous_number <> new_number",
            name="ck_box_number_history_changed",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_number_history_reason_not_empty",
        ),
        Index("ix_box_number_history_box_id", "box_id", "changed_at"),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_number: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class BoxMovement(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "box_movements"
    __table_args__ = (
        check_in("movement_type", MovementType, name="ck_box_movements_type"),
        check_in("movement_status", MovementStatus, name="ck_box_movements_status"),
        CheckConstraint(
            "from_position_id IS NULL OR to_position_id IS NULL "
            "OR from_position_id <> to_position_id",
            name="ck_box_movements_position_change",
        ),
        CheckConstraint(
            "movement_status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_box_movements_completed_at",
        ),
        CheckConstraint(
            "movement_status <> 'CANCELLED' OR cancelled_at IS NOT NULL",
            name="ck_box_movements_cancelled_at",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_movements_reason_not_empty",
        ),
        Index("ix_box_movements_box", "box_id", "occurred_at"),
        Index("ix_box_movements_status", "movement_status"),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(String(24), nullable=False)
    movement_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=MovementStatus.PLANNED.value,
        server_default=MovementStatus.PLANNED.value,
    )
    from_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    to_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    loan_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    performed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
