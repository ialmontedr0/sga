from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
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

from judicial_archive.core.enums import (
    FindingStatus,
    FindingType,
    InventoryScopeType,
    InventoryStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class InventorySession(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "inventory_sessions"
    __table_args__ = (
        check_in(
            "scope_type",
            InventoryScopeType,
            name="ck_inventory_sessions_scope_type",
        ),
        check_in("status", InventoryStatus, name="ck_inventory_sessions_status"),
        CheckConstraint(
            "scanned_count >= 0 AND expected_count >= 0",
            name="ck_inventory_sessions_counts",
        ),
        CheckConstraint(
            "("
            "(scope_type = 'AREA' AND area_id IS NOT NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'SHELF' AND area_id IS NULL "
            "AND shelf_id IS NOT NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'TRAY' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NOT NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'POSITION_RANGE' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NOT NULL AND end_position_id IS NOT NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'BOX' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NOT NULL)"
            ")",
            name="ck_inventory_sessions_scope_columns",
        ),
        CheckConstraint(
            "status <> 'CLOSED' OR closed_at IS NOT NULL",
            name="ck_inventory_sessions_closed_at",
        ),
        CheckConstraint(
            "summary IS NULL OR jsonb_typeof(summary) = 'object'",
            name="ck_inventory_sessions_summary_object",
        ),
        CheckConstraint(
            "length(btrim(code)) > 0",
            name="ck_inventory_sessions_code_not_empty",
        ),
        Index("ix_inventory_sessions_status", "status"),
        Index("ix_inventory_sessions_scope", "scope_type"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scope_type: Mapped[str] = mapped_column(String(24), nullable=False)
    area_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    shelf_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tray_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("trays.id", ondelete="RESTRICT"),
        nullable=True,
    )
    start_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    end_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=InventoryStatus.DRAFT.value,
        server_default=InventoryStatus.DRAFT.value,
    )
    responsible_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    scanned_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class InventoryFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_findings"
    __table_args__ = (
        check_in("finding_type", FindingType, name="ck_inventory_findings_type"),
        check_in("finding_status", FindingStatus, name="ck_inventory_findings_status"),
        CheckConstraint(
            "expected_data IS NULL OR jsonb_typeof(expected_data) = 'object'",
            name="ck_inventory_findings_expected_object",
        ),
        CheckConstraint(
            "observed_data IS NULL OR jsonb_typeof(observed_data) = 'object'",
            name="ck_inventory_findings_observed_object",
        ),
        CheckConstraint(
            "finding_status NOT IN ('RESOLVED', 'ACCEPTED_DIFFERENCE') "
            "OR (resolution IS NOT NULL "
            "AND length(btrim(resolution)) > 0 "
            "AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)",
            name="ck_inventory_findings_resolution_fields",
        ),
        Index("ix_inventory_findings_session", "session_id", "finding_status"),
        Index("ix_inventory_findings_box", "box_id"),
    )

    session_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("inventory_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FindingStatus.OPEN.value,
        server_default=FindingStatus.OPEN.value,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expected_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    observed_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expected_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    observed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
