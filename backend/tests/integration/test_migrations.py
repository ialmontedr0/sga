from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.modules.boxes.models import Box
from tests.integration.location_fixtures import create_location_tree

pytestmark = pytest.mark.integration


def _exists(url: str, name: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return (
                connection.scalar(
                    text("SELECT to_regclass(:name)"),
                    {"name": f"public.{name}"},
                )
                is not None
            )
    finally:
        engine.dispose()


def _index_exists(url: str, name: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return bool(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_indexes "
                        "WHERE schemaname = 'public' AND indexname = :name"
                    ),
                    {"name": name},
                )
            )
    finally:
        engine.dispose()


def _trigger_exists(url: str, name: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return bool(
                connection.scalar(
                    text("SELECT count(*) FROM pg_trigger WHERE tgname = :name"),
                    {"name": name},
                )
            )
    finally:
        engine.dispose()


def _function_exists(url: str, name: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return bool(
                connection.scalar(
                    text("SELECT count(*) FROM pg_proc WHERE proname = :name"),
                    {"name": name},
                )
            )
    finally:
        engine.dispose()


def _column_exists(url: str, table: str, column: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return bool(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :table "
                        "AND column_name = :column"
                    ),
                    {"table": table, "column": column},
                )
            )
    finally:
        engine.dispose()


def _constraint_def(url: str, table: str, name: str) -> str | None:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            result = connection.scalar(
                text(
                    "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid "
                    "WHERE t.relname = :table AND c.conname = :name"
                ),
                {"table": table, "name": name},
            )
            return str(result) if result is not None else None
    finally:
        engine.dispose()


def test_upgrade_downgrade_round_trip(
    alembic_config: Config,
    test_database_url: str,
) -> None:
    try:
        command.upgrade(alembic_config, "head")
        assert _exists(test_database_url, "boxes")
        assert _exists(test_database_url, "audit_events")

        command.downgrade(alembic_config, "base")
        assert not _exists(test_database_url, "boxes")
        assert not _exists(test_database_url, "audit_events")
    finally:
        command.upgrade(alembic_config, "head")


def test_alembic_check_is_clean(
    alembic_config: Config,
    test_database_url: str,
) -> None:
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)


@pytest.mark.asyncio
async def test_b6_objects_round_trip(
    alembic_config: Config,
    test_database_url: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    command.upgrade(alembic_config, "head")

    try:
        assert _exists(test_database_url, "box_location_history")
        assert _index_exists(test_database_url, "ix_box_location_history_box_changed")
        assert _index_exists(test_database_url, "uq_box_movements_open_box")
        assert _trigger_exists(test_database_url, "trg_box_location_history_append_only")
        assert _trigger_exists(test_database_url, "trg_box_location_history_no_truncate")
        assert _function_exists(test_database_url, "sga_location_history_append_only")
        assert _column_exists(test_database_url, "position_blocks", "cancellation_reason")
        assert "PENDING_VERIFICATION" in (
            _constraint_def(test_database_url, "boxes", "ck_boxes_custody_status") or ""
        )
        assert "UNASSIGN" in (
            _constraint_def(test_database_url, "box_movements", "ck_box_movements_type") or ""
        )

        command.downgrade(alembic_config, "-1")

        objects_after_downgrade = {
            "table: box_location_history": _exists(test_database_url, "box_location_history"),
            "index: uq_box_movements_open_box": _index_exists(
                test_database_url, "uq_box_movements_open_box"
            ),
            "trigger: trg_box_location_history_append_only": _trigger_exists(
                test_database_url, "trg_box_location_history_append_only"
            ),
            "trigger: trg_box_location_history_no_truncate": _trigger_exists(
                test_database_url, "trg_box_location_history_no_truncate"
            ),
            "function: sga_location_history_append_only": _function_exists(
                test_database_url, "sga_location_history_append_only"
            ),
            "column: position_blocks.cancellation_reason": _column_exists(
                test_database_url,
                "position_blocks",
                "cancellation_reason",
            ),
        }

        remaining_objects = [name for name, exists in objects_after_downgrade.items() if exists]

        assert not remaining_objects, (
            "Los siguientes objetos de B6 siguen existiendo después del downgrade: "
            f"{remaining_objects}"
        )
    finally:
        command.upgrade(alembic_config, "head")


@pytest.mark.asyncio
async def test_b6_downgrade_rejects_incompatible_data(
    alembic_config: Config,
    test_database_url: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    command.upgrade(alembic_config, "head")
    tree = await create_location_tree(session_factory)

    async with session_factory() as session:
        await session.execute(
            update(Box)
            .where(Box.id == tree.box_ids[0])
            .values(
                custody_status="PENDING_VERIFICATION",
                current_position_id=tree.position_ids[0],
            )
        )
        await session.commit()

    with pytest.raises(DBAPIError):
        command.downgrade(alembic_config, "-1")

    async with session_factory() as session:
        await session.execute(
            update(Box)
            .where(Box.id == tree.box_ids[0])
            .values(custody_status="UNKNOWN", current_position_id=None)
        )
        await session.commit()

    command.upgrade(alembic_config, "head")
    assert _exists(test_database_url, "box_location_history")
