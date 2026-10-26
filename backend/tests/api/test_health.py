from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


class _HealthyDatabase:
    class _Engine:
        class _Connection:
            async def __aenter__(self) -> _HealthyDatabase._Engine._Connection:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def execute(self, *args: object, **kwargs: object) -> None:
                return None

        def connect(self) -> _HealthyDatabase._Engine._Connection:
            return self._Connection()

    engine = _Engine()


class _BrokenDatabase:
    class _Engine:
        def connect(self) -> Any:
            raise RuntimeError("no disponible")

    engine = _Engine()


class _HealthyRedis:
    async def ping(self, **kwargs: object) -> bool:
        return True


class _BrokenRedis:
    async def ping(self, **kwargs: object) -> bool:
        raise RuntimeError("no disponible")


def _client_with_state(database: object, redis: object) -> TestClient:
    app = create_app(build_test_settings(), configure_logs=False)
    client = TestClient(app)
    client.__enter__()
    app.state.database = database
    app.state.redis = redis
    return client


def test_liveness_returns_ok() -> None:
    client = _client_with_state(_BrokenDatabase(), _BrokenRedis())
    try:
        response = client.get("/api/v1/health/live")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_liveness_preserves_valid_request_id() -> None:
    client = _client_with_state(_BrokenDatabase(), _BrokenRedis())
    try:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "abc12345"},
        )
    finally:
        client.__exit__(None, None, None)
    assert response.headers["X-Request-ID"] == "abc12345"


def test_ready_when_dependencies_are_healthy() -> None:
    client = _client_with_state(_HealthyDatabase(), _HealthyRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_not_ready_when_database_fails() -> None:
    client = _client_with_state(_BrokenDatabase(), _HealthyRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 503
    assert response.json()["components"]["database"]["status"] == "error"


def test_not_ready_when_redis_fails() -> None:
    client = _client_with_state(_HealthyDatabase(), _BrokenRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 503
    assert response.json()["components"]["redis"]["status"] == "error"
