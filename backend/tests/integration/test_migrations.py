from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

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
