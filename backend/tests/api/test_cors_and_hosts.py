from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def test_cors_preflight_allowed_origin() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_disallowed_origin_has_no_allow_header() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://evil.example"},
        )
    assert "access-control-allow-origin" not in response.headers


def test_trusted_host_allowed() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["testserver"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200


def test_trusted_host_wildcard_allows_subdomain() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["*.example.com"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Host": "archivo.example.com"},
        )
    assert response.status_code == 200


def test_trusted_host_rejects_invalid_header() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["example.com"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Host": "host invalido"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_trusted_host_rejected() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["example.com"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Host": "evil.example"},
        )
    body = response.json()
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/json"
    assert response.headers["X-Request-ID"]
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]


def test_trusted_host_rejection_keeps_cors_headers() -> None:
    app = create_app(
        build_test_settings(
            trusted_hosts=["example.com"],
            cors_origins=["http://localhost:5173"],
        ),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Host": "evil.example", "Origin": "http://localhost:5173"},
        )
    assert response.status_code == 400
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_request_id_on_cors_response() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://localhost:5173"},
        )
    assert response.headers["X-Request-ID"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_no_cors_headers_when_no_origins() -> None:
    app = create_app(build_test_settings(cors_origins=[]), configure_logs=False)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://localhost:5173"},
        )
    assert "access-control-allow-origin" not in response.headers
