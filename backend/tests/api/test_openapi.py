from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def test_openapi_contains_only_real_health_paths() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths
    assert not any("boxes" in path for path in paths)


def test_docs_available_when_enabled() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_disabled() -> None:
    app = create_app(build_test_settings(docs_enabled=False), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 404


def test_docs_disabled() -> None:
    app = create_app(build_test_settings(docs_enabled=False), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/docs")
    assert response.status_code == 404


def test_readiness_schema_is_documented() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    schemas = response.json()["components"]["schemas"]
    assert "ReadinessStatus" in schemas
    assert "components" in schemas["ReadinessStatus"]["properties"]


def test_health_tag_is_documented() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    tags = response.json()["tags"]
    assert any(tag["name"] == "Salud" for tag in tags)
