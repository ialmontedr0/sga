from __future__ import annotations

from typing import Any, cast

from judicial_archive.db.health import check_database, check_redis
from judicial_archive.db.session import Database


class _FakeConnection:
    async def __aenter__(self) -> _FakeConnection:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def execute(self, statement: object) -> None:
        return None


class _FakeEngine:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def connect(self) -> _FakeConnection:
        if self._fail:
            raise RuntimeError("conexion simulada fallida")
        return _FakeConnection()


class _FakeDatabase:
    def __init__(self, *, fail: bool = False) -> None:
        self.engine = _FakeEngine(fail=fail)


class _FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def ping(self, **kwargs: Any) -> bool:
        if self._fail:
            raise RuntimeError("redis simulado fallido")
        return True


async def test_database_health_ok() -> None:
    health = await check_database(cast(Database, _FakeDatabase()), 1.0)

    assert health.status == "ok"
    assert health.latency_ms >= 0


async def test_database_health_failure() -> None:
    health = await check_database(cast(Database, _FakeDatabase(fail=True)), 1.0)

    assert health.status == "error"
    assert health.latency_ms >= 0


async def test_redis_health_ok() -> None:
    health = await check_redis(_FakeRedis(), 1.0)

    assert health.status == "ok"


async def test_redis_health_failure() -> None:
    health = await check_redis(_FakeRedis(fail=True), 1.0)

    assert health.status == "error"
