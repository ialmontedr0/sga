from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.core.middleware import CSRFMiddleware
from tests.helpers import build_test_settings


def _build_app(settings: Settings) -> FastAPI:
    app = FastAPI()

    @app.get("/read")
    def read() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/mutate")
    def mutate() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/auth/csrf")
    def csrf_exempt() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(
        CSRFMiddleware,
        settings=settings,
        exempt_paths=("/api/v1/auth/csrf",),
    )
    return app


def _client(settings: Settings) -> TestClient:
    return TestClient(_build_app(settings))


def test_safe_method_without_csrf_is_allowed() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        assert client.get("/read").status_code == 200


def test_unsafe_method_without_csrf_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        response = client.post("/mutate")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_unsafe_method_with_cookie_but_no_header_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, "token-value")
        response = client.post("/mutate")
    assert response.status_code == 403


def test_unsafe_method_with_mismatched_tokens_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, "cookie-value")
        response = client.post("/mutate", headers={settings.auth_csrf_header_name: "header-value"})
    assert response.status_code == 403


def test_unsafe_method_with_matching_tokens_is_allowed() -> None:
    settings = build_test_settings()
    token = "matching-token-value"
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, token)
        response = client.post("/mutate", headers={settings.auth_csrf_header_name: token})
    assert response.status_code == 200


def test_exempt_path_is_allowed() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        response = client.post("/api/v1/auth/csrf")
    assert response.status_code == 200


def test_disabled_csrf_allows_unsafe_methods() -> None:
    settings = build_test_settings(auth_csrf_enabled=False)
    with _client(settings) as client:
        response = client.post("/mutate")
    assert response.status_code == 200
