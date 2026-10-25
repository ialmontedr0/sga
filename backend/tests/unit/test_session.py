from __future__ import annotations

from judicial_archive.db.session import Database
from tests.helpers import build_test_settings


async def test_database_is_created_and_disposed_without_connecting() -> None:
    database = Database(build_test_settings())

    assert database.engine is not None
    async with database.session() as session:
        assert session is not None

    await database.dispose()
