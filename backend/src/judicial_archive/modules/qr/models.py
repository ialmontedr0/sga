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

from judicial_archive.db.base import Base
from judicial_archive.db.mixins import UUIDPrimaryKeyMixin


class BoxLabel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "box_labels"
    __table_args__ = (
        CheckConstraint(
            "length(token_hash) > 0",
            name="ck_box_labels_token_hash_not_empty",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= issued_at",
            name="ck_box_labels_revoked_after_issue",
        ),
        Index(
            "ix_box_labels_box_active",
            "box_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default=text("1"))
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    issued_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
