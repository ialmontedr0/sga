from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient


def _openapi(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_administrative_documents_openapi_contains_required_paths(
    client: TestClient,
) -> None:
    paths = _openapi(client)["paths"]

    assert "/api/v1/administrative-documents" in paths
    assert "/api/v1/administrative-documents/duplicates" in paths
    assert "/api/v1/administrative-documents/{document_id}" in paths
    assert "/api/v1/administrative-documents/{document_id}/archive" in paths
    assert "/api/v1/administrative-documents/{document_id}/void" in paths


def test_administrative_document_delete_is_soft_delete_endpoint(
    client: TestClient,
) -> None:
    paths = _openapi(client)["paths"]
    operations = paths["/api/v1/administrative-documents/{document_id}"]

    assert "delete" in operations


def test_administrative_document_create_schema_requires_box_title_and_year(
    client: TestClient,
) -> None:
    schemas = _openapi(client)["components"]["schemas"]
    required = set(schemas["AdministrativeDocumentCreate"]["required"])

    assert {"box_id", "title", "document_year"} <= required


def test_administrative_document_reads_require_authentication(
    client: TestClient,
) -> None:
    for path in (
        "/api/v1/administrative-documents",
        f"/api/v1/administrative-documents/{uuid4()}",
    ):
        response = client.get(path)
        assert response.status_code == 401, path


def test_administrative_document_creation_requires_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/administrative-documents",
        json={
            "box_id": str(uuid4()),
            "title": "Oficio de prueba",
            "document_year": 2026,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}
