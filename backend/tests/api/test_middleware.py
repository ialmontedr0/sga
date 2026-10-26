from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def _client(**overrides: object) -> TestClient:
    settings: Settings = build_test_settings(**overrides)
    return TestClient(create_app(settings, configure_logs=False))


def test_request_id_is_generated() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/live")
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert response.json()["status"] == "ok"


def test_valid_request_id_is_preserved() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "abc12345"},
        )
    assert response.headers["X-Request-ID"] == "abc12345"


def test_invalid_request_id_is_replaced() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "<script>alert(1)</script>"},
        )
    assert response.headers["X-Request-ID"] != "<script>alert(1)</script>"
    assert len(response.headers["X-Request-ID"]) == 32


def test_request_id_on_not_found() -> None:
    with _client() as client:
        response = client.get("/ruta-inexistente")
    assert response.status_code == 404
    assert response.headers["X-Request-ID"]
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_body_over_limit_returns_413() -> None:
    with _client(max_request_body_bytes=1024) as client:
        response = client.post(
            "/api/v1/health/live",
            content=b"x" * 1025,
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert response.json()["error"]["details"] == {"max_bytes": 1024}


def test_body_over_limit_keeps_cors_and_request_id() -> None:
    with _client(
        cors_origins=["http://localhost:5173"],
        max_request_body_bytes=1024,
    ) as client:
        response = client.post(
            "/api/v1/health/live",
            headers={"Origin": "http://localhost:5173"},
            content=b"x" * 1025,
        )
    assert response.status_code == 413
    assert response.headers["X-Request-ID"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_body_within_limit_reaches_app() -> None:
    with _client(max_request_body_bytes=1024) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200


def test_invalid_content_length_returns_400() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/health/live",
            headers={"Content-Length": "abc"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_request_id_present_on_validation_error() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/ready?x=1")
    assert response.headers["X-Request-ID"]
