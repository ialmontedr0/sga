from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import OcrStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class OcrResult(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        check_in("status", OcrStatus, name="ck_ocr_results_status"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_ocr_results_confidence_range",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_ocr_results_metadata_object",
        ),
        CheckConstraint(
            "status <> 'ACCEPTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_ocr_results_accepted_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_ocr_results_rejected_fields",
        ),
        CheckConstraint(
            "status NOT IN ('COMPLETED', 'ACCEPTED', 'REVIEW_REQUIRED') OR text IS NOT NULL",
            name="ck_ocr_results_completed_text",
        ),
        Index("ix_ocr_results_file_asset", "file_asset_id"),
        Index("ix_ocr_results_import_file", "import_file_id"),
        Index("ix_ocr_results_status", "status"),
    )

    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("import_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    engine_name: Mapped[str] = mapped_column(String(80), nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=OcrStatus.PENDING.value,
        server_default=OcrStatus.PENDING.value,
    )
    text: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
