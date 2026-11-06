from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient


def _openapi(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_case_files_openapi_contains_required_paths(client: TestClient) -> None:
    paths = _openapi(client)["paths"]

    assert "/api/v1/case-files" in paths
    assert "/api/v1/case-files/duplicates" in paths
    assert "/api/v1/case-files/{case_file_id}" in paths
    assert "/api/v1/case-files/{case_file_id}/identifiers/correct" in paths
    assert "/api/v1/case-files/{case_file_id}/relocate" in paths
    assert "/api/v1/case-files/{case_file_id}/parties" in paths
    assert "/api/v1/case-files/{case_file_id}/parties/with-person" in paths
    assert "/api/v1/persons" in paths
    assert "/api/v1/persons/duplicates" in paths
    assert "/api/v1/persons/{person_id}" in paths


def test_case_file_delete_is_soft_delete_endpoint(client: TestClient) -> None:
    paths = _openapi(client)["paths"]
    operations = paths["/api/v1/case-files/{case_file_id}"]

    assert "delete" in operations


def test_duplicate_schemas_expose_match_types(client: TestClient) -> None:
    schemas = _openapi(client)["components"]["schemas"]

    assert "match_type" in schemas["DuplicateCaseFileOut"]["properties"]
    assert "match_type" in schemas["DuplicatePersonOut"]["properties"]


def test_case_file_reads_require_authentication(client: TestClient) -> None:
    for path in (
        "/api/v1/case-files",
        f"/api/v1/case-files/duplicates?court_id={uuid4()}&nuc=NUC-2026-0001&year=2026",
        "/api/v1/persons",
        "/api/v1/persons/duplicates?display_name=Persona",
        f"/api/v1/case-files/{uuid4()}",
    ):
        response = client.get(path)
        assert response.status_code == 401, path


def test_case_file_creation_requires_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/case-files",
        json={
            "court_id": str(uuid4()),
            "nuc": "NUC-2026-0001",
            "year": 2026,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}
