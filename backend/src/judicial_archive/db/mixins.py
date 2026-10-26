from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def enum_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


def check_in(column: str, enum_type: type[StrEnum], *, name: str) -> CheckConstraint:
    return CheckConstraint(f"{column} IN ({enum_values(enum_type)})", name=name)


def check_jsonb_object(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR jsonb_typeof({column}) = 'object'",
        name=name,
    )


def check_jsonb_array(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR jsonb_typeof({column}) = 'array'",
        name=name,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OptimisticLockMixin:
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.version}


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


def non_empty_text(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(f"length(btrim({column})) > 0", name=name)


def partial_date_checks(
    table_name: str,
    prefix: str,
) -> tuple[CheckConstraint, CheckConstraint, CheckConstraint]:
    year = f"{prefix}_year"
    month = f"{prefix}_month"
    day = f"{prefix}_day"
    precision = f"{prefix}_precision"
    check_precision = CheckConstraint(
        f"{precision} IN ('UNKNOWN', 'YEAR', 'MONTH', 'DAY')",
        name=f"ck_{table_name}_{prefix}_precision",
    )
    check_shape = CheckConstraint(
        "("
        f"({precision} = 'UNKNOWN' AND {year} IS NULL AND {month} IS NULL AND {day} IS NULL)"
        f" OR ({precision} = 'YEAR' AND {year} IS NOT NULL AND {month} IS NULL AND {day} IS NULL)"
        f" OR ({precision} = 'MONTH' AND {year} IS NOT NULL AND {month} IS NOT NULL AND {day} IS NULL)"
        f" OR ({precision} = 'DAY' AND {year} IS NOT NULL AND {month} IS NOT NULL AND {day} IS NOT NULL)"
        ")",
        name=f"ck_{table_name}_{prefix}_shape",
    )
    check_ranges = CheckConstraint(
        f"({year} IS NULL OR {year} BETWEEN 1 AND 9999)"
        f" AND ({month} IS NULL OR {month} BETWEEN 1 AND 12)"
        f" AND ({day} IS NULL OR {day} BETWEEN 1 AND 31)",
        name=f"ck_{table_name}_{prefix}_ranges",
    )
    return check_precision, check_shape, check_ranges
