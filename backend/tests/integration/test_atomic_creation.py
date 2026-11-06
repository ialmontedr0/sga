from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)
from tests.integration.b7_helpers import active_court_id

pytestmark = pytest.mark.integration


def test_create_box_with_case_files_atomically(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    response = client.post(
        "/api/v1/boxes/with-content",
        json={
            "box": {
                "court_id": court_id,
                "year": 2026,
                "box_type": "EXPEDIENTES",
                "description": "Caja atomica con expediente",
            },
            "case_files": [{"nuc": "NUC-2026-2001", "year": 2026}],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    payload = cast(dict[str, Any], response.json())
    assert payload["box"]["box_type"] == "EXPEDIENTES"
    assert len(payload["case_file_ids"]) == 1
    assert payload["administrative_document_ids"] == []
    assert payload["warnings"]

    case_file_id = payload["case_file_ids"][0]
    detail = client.get(f"/api/v1/case-files/{case_file_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["box_id"] == payload["box"]["id"]

    summary = client.get(f"/api/v1/boxes/{payload['box']['id']}/content-summary")
    assert summary.status_code == 200, summary.text
    assert summary.json()["case_file_count"] == 1
    assert summary.json()["total_count"] == 1


def test_create_box_with_administrative_documents_atomically(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    response = client.post(
        "/api/v1/boxes/with-content",
        json={
            "box": {
                "court_id": court_id,
                "year": 2026,
                "box_type": "DOCUMENTOS_ADMINISTRATIVOS",
                "description": "Caja atomica administrativa",
            },
            "administrative_documents": [{"title": "Oficio atomico", "document_year": 2026}],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    payload = cast(dict[str, Any], response.json())
    assert payload["case_file_ids"] == []
    assert len(payload["administrative_document_ids"]) == 1

    document_id = payload["administrative_document_ids"][0]
    detail = client.get(f"/api/v1/administrative-documents/{document_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["box_id"] == payload["box"]["id"]


def test_duplicate_case_file_rolls_back_box_creation(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    response = client.post(
        "/api/v1/boxes/with-content",
        json={
            "box": {
                "court_id": court_id,
                "year": 2026,
                "box_type": "EXPEDIENTES",
            },
            "case_files": [
                {"nuc": "NUC-2026-2002", "year": 2026},
                {"nuc": "nuc-2026-2002", "year": 2026},
            ],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_nuc"

    boxes = client.get("/api/v1/boxes", params={"court_id": court_id})
    assert boxes.status_code == 200, boxes.text
    assert boxes.json()["total"] == 0

    case_files = client.get("/api/v1/case-files", params={"court_id": court_id})
    assert case_files.status_code == 200, case_files.text
    assert case_files.json()["total"] == 0


def test_duplicate_administrative_document_rolls_back_box_creation(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    response = client.post(
        "/api/v1/boxes/with-content",
        json={
            "box": {
                "court_id": court_id,
                "year": 2026,
                "box_type": "DOCUMENTOS_ADMINISTRATIVOS",
            },
            "administrative_documents": [
                {"title": "Oficio repetido", "document_year": 2026},
                {"title": "Oficio repetido", "document_year": 2026},
            ],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_administrative_document"

    boxes = client.get("/api/v1/boxes", params={"court_id": court_id})
    assert boxes.status_code == 200, boxes.text
    assert boxes.json()["total"] == 0


def test_mixed_content_is_rejected_before_persistence(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    response = client.post(
        "/api/v1/boxes/with-content",
        json={
            "box": {
                "court_id": court_id,
                "year": 2026,
                "box_type": "EXPEDIENTES",
            },
            "case_files": [{"nuc": "NUC-2026-2003", "year": 2026}],
            "administrative_documents": [{"title": "Oficio mezclado", "document_year": 2026}],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 422
    boxes = client.get("/api/v1/boxes", params={"court_id": court_id})
    assert boxes.status_code == 200, boxes.text
    assert boxes.json()["total"] == 0
