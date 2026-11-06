from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient


def _openapi(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_boxes_openapi_contains_required_paths(client: TestClient) -> None:
    paths = _openapi(client)["paths"]

    assert "/api/v1/boxes" in paths
    assert "/api/v1/boxes/with-content" in paths
    assert "/api/v1/boxes/{box_id}" in paths
    assert "/api/v1/boxes/{box_id}/content-summary" in paths
    assert "/api/v1/boxes/{box_id}/number-history" in paths
    assert "/api/v1/boxes/{box_id}/number-corrections" in paths
    assert "/api/v1/boxes/{box_id}/archive" in paths
    assert "/api/v1/boxes/{box_id}/void" in paths


def test_boxes_do_not_expose_delete(client: TestClient) -> None:
    paths = _openapi(client)["paths"]
    operations = paths["/api/v1/boxes/{box_id}"]

    assert "delete" not in operations


def test_box_with_content_schema_uses_inline_content(client: TestClient) -> None:
    schemas = _openapi(client)["components"]["schemas"]
    properties = schemas["BoxWithContentCreate"]["properties"]

    assert {"box", "case_files", "administrative_documents"} <= set(properties)
    assert "warnings" not in properties
    assert "BoxWithContentOut" in schemas


def test_box_create_schema_requires_court_year_and_type(client: TestClient) -> None:
    schemas = _openapi(client)["components"]["schemas"]
    required = set(schemas["BoxCreate"]["required"])

    assert {"court_id", "year", "box_type"} <= required


def test_box_reads_require_authentication(client: TestClient) -> None:
    for path in ("/api/v1/boxes", f"/api/v1/boxes/{uuid4()}"):
        response = client.get(path)
        assert response.status_code == 401, path


def test_box_creation_requires_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/boxes",
        json={
            "court_id": str(uuid4()),
            "year": 2026,
            "box_type": "EXPEDIENTES",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}
