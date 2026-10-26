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
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import AreaStatus, PositionStatus, ShelfStatus, TrayStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Area(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "areas"
    __table_args__ = (
        check_in("status", AreaStatus, name="ck_areas_status"),
        CheckConstraint("code ~ '^[A-Z][A-Z0-9-]{0,15}$'", name="ck_areas_code_format"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_areas_name_not_empty"),
    )

    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AreaStatus.ACTIVE.value,
        server_default=AreaStatus.ACTIVE.value,
    )


class Shelf(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("area_id", "code", name="uq_shelves_area_code"),
        check_in("status", ShelfStatus, name="ck_shelves_status"),
        CheckConstraint(
            "code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'",
            name="ck_shelves_code_format",
        ),
        CheckConstraint(
            "(levels IS NULL AND positions_per_level IS NULL) OR "
            "(levels IS NOT NULL AND positions_per_level IS NOT NULL)",
            name="ck_shelves_capacity_pair",
        ),
        CheckConstraint(
            "levels IS NULL OR levels > 0",
            name="ck_shelves_levels_positive",
        ),
        CheckConstraint(
            "positions_per_level IS NULL OR positions_per_level > 0",
            name="ck_shelves_positions_positive",
        ),
        Index("ix_shelves_area_id", "area_id"),
    )

    area_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    levels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positions_per_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_positions: Mapped[int | None] = mapped_column(
        Integer,
        Computed("levels * positions_per_level", persisted=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ShelfStatus.ACTIVE.value,
        server_default=ShelfStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Tray(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "trays"
    __table_args__ = (
        UniqueConstraint("shelf_id", "code", name="uq_trays_shelf_code"),
        check_in("status", TrayStatus, name="ck_trays_status"),
        CheckConstraint(
            "code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'",
            name="ck_trays_code_format",
        ),
        CheckConstraint(
            "position_count IS NULL OR position_count > 0",
            name="ck_trays_position_count",
        ),
        Index("ix_trays_shelf_id", "shelf_id"),
    )

    shelf_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    position_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TrayStatus.ACTIVE.value,
        server_default=TrayStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Position(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("tray_id", "code", name="uq_positions_tray_code"),
        check_in("status", PositionStatus, name="ck_positions_status"),
        CheckConstraint(
            "length(btrim(code)) > 0",
            name="ck_positions_code_not_empty",
        ),
        CheckConstraint(
            "length(btrim(label)) > 0",
            name="ck_positions_label_not_empty",
        ),
        Index("ix_positions_tray_id", "tray_id"),
        Index("ix_positions_status", "status"),
    )

    tray_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("trays.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PositionStatus.AVAILABLE.value,
        server_default=PositionStatus.AVAILABLE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class PositionBlock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "position_blocks"
    __table_args__ = (
        CheckConstraint(
            "first_position_number > 0",
            name="ck_position_blocks_first_number",
        ),
        CheckConstraint(
            "last_position_number >= first_position_number",
            name="ck_position_blocks_range",
        ),
        CheckConstraint(
            "cancelled_at IS NULL OR cancelled_at >= created_at",
            name="ck_position_blocks_cancel_after_creation",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_position_blocks_reason_not_empty",
        ),
        Index(
            "ix_position_blocks_shelf_active",
            "shelf_id",
            "start_position_id",
            "end_position_id",
        ),
    )

    shelf_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_position_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    end_position_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    first_position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    last_position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    blocked_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
