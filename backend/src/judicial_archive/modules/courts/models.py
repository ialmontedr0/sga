from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
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
    CatalogStatus,
    CourtStatus,
    IdentifierKind,
    NumberingScope,
    ResetPolicy,
    RetentionDisposition,
    RetentionEntityType,
    SettingValueType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Court(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "courts"
    __table_args__ = (
        check_in("status", CourtStatus, name="ck_courts_status"),
        CheckConstraint(
            "code_normalized = upper(btrim(code_raw))",
            name="ck_courts_code_normalized",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_courts_name_not_empty",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_courts_effective_range",
        ),
        Index("ix_courts_status", "status"),
        Index("ix_courts_name", "name"),
    )

    code_raw: Mapped[str] = mapped_column(String(), nullable=False)
    code_normalized: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    court_type: Mapped[str | None] = mapped_column(String(), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CourtStatus.ACTIVE.value,
        server_default=CourtStatus.ACTIVE.value,
    )
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class IdentifierFormatProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "identifier_format_profiles"
    __table_args__ = (
        check_in(
            "identifier_kind",
            IdentifierKind,
            name="ck_identifier_format_profiles_kind",
        ),
        CheckConstraint(
            "strict = false OR pattern IS NOT NULL",
            name="ck_identifier_format_profiles_strict_pattern",
        ),
        CheckConstraint(
            "examples IS NULL OR jsonb_typeof(examples) = 'array'",
            name="ck_identifier_format_profiles_examples_array",
        ),
        CheckConstraint(
            "rejects IS NULL OR jsonb_typeof(rejects) = 'array'",
            name="ck_identifier_format_profiles_rejects_array",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_identifier_format_profiles_effective_range",
        ),
        Index(
            "ix_identifier_format_profiles_court_kind",
            "court_id",
            "identifier_kind",
        ),
        Index(
            "uq_identifier_format_profiles_active",
            "court_id",
            "identifier_kind",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tokens: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    examples: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    rejects: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    strict: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ResolutionType(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "resolution_types"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_resolution_types_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9_]{1,31}$'",
            name="ck_resolution_types_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_resolution_types_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )


class NumberingPolicy(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "numbering_policies"
    __table_args__ = (
        check_in("scope", NumberingScope, name="ck_numbering_policies_scope"),
        check_in("reset_policy", ResetPolicy, name="ck_numbering_policies_reset"),
        check_in("box_type", BoxType, name="ck_numbering_policies_box_type"),
        CheckConstraint(
            "("
            "(scope = 'GLOBAL' AND court_id IS NULL AND box_type IS NULL AND year IS NULL)"
            " OR (scope = 'COURT' AND court_id IS NOT NULL AND box_type IS NULL AND year IS NULL)"
            " OR (scope = 'BOX_TYPE' AND court_id IS NULL AND box_type IS NOT NULL AND year IS NULL)"
            " OR (scope = 'YEAR' AND court_id IS NULL AND box_type IS NULL AND year IS NOT NULL)"
            ")",
            name="ck_numbering_policies_scope_columns",
        ),
        CheckConstraint(
            "padding BETWEEN 0 AND 12",
            name="ck_numbering_policies_padding",
        ),
        CheckConstraint(
            "start_value > 0",
            name="ck_numbering_policies_start_value",
        ),
        CheckConstraint(
            "step > 0",
            name="ck_numbering_policies_step",
        ),
        CheckConstraint(
            "length(btrim(sequence_name)) > 0",
            name="ck_numbering_policies_sequence_name",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_numbering_policies_effective_range",
        ),
        Index(
            "uq_numbering_policies_active_global",
            "scope",
            unique=True,
            postgresql_where=text("is_active AND scope = 'GLOBAL'"),
        ),
        Index(
            "uq_numbering_policies_active_court",
            "court_id",
            unique=True,
            postgresql_where=text("is_active AND scope = 'COURT'"),
        ),
        Index(
            "uq_numbering_policies_active_box_type",
            "box_type",
            unique=True,
            postgresql_where=text("is_active AND scope = 'BOX_TYPE'"),
        ),
        Index(
            "uq_numbering_policies_active_year",
            "year",
            unique=True,
            postgresql_where=text("is_active AND scope = 'YEAR'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    court_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_name: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    prefix: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(32), nullable=True)
    padding: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    start_value: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    reset_policy: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ResetPolicy.NEVER.value,
        server_default=ResetPolicy.NEVER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class RetentionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "retention_policies"
    __table_args__ = (
        check_in(
            "entity_type",
            RetentionEntityType,
            name="ck_retention_policies_entity_type",
        ),
        check_in(
            "disposition",
            RetentionDisposition,
            name="ck_retention_policies_disposition",
        ),
        check_in("box_type", BoxType, name="ck_retention_policies_box_type"),
        CheckConstraint(
            "retention_months IS NULL OR retention_months > 0",
            name="ck_retention_policies_months",
        ),
        CheckConstraint(
            "is_active = false OR length(btrim(legal_basis)) > 0",
            name="ck_retention_policies_active_legal_basis",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_retention_policies_effective_range",
        ),
        Index(
            "ix_retention_policies_lookup",
            "entity_type",
            "court_id",
            "box_type",
            "is_active",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    court_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    retention_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        check_in(
            "value_type",
            SettingValueType,
            name="ck_system_settings_value_type",
        ),
        CheckConstraint(
            "key ~ '^[a-z][a-z0-9_.-]{2,127}$'",
            name="ck_system_settings_key_format",
        ),
        CheckConstraint(
            "("
            "(value_type = 'STRING' AND jsonb_typeof(value) = 'string')"
            " OR (value_type = 'INTEGER' AND jsonb_typeof(value) = 'number')"
            " OR (value_type = 'BOOLEAN' AND jsonb_typeof(value) = 'boolean')"
            " OR (value_type = 'JSON' AND jsonb_typeof(value) IN ('object', 'array'))"
            ")",
            name="ck_system_settings_value_matches_type",
        ),
        CheckConstraint(
            "length(btrim(description)) > 0",
            name="ck_system_settings_description_not_empty",
        ),
    )

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class PartyRole(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "party_roles"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_party_roles_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9_]{1,63}$'",
            name="ck_party_roles_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_party_roles_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )
