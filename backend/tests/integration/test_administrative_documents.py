from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)
from tests.integration.b7_helpers import (
    active_court_id,
    create_administrative_document,
    create_box,
)

pytestmark = pytest.mark.integration


def test_create_and_get_administrative_document(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )

    document = create_administrative_document(
        client,
        box_id=box["id"],
        title="Oficio de prueba",
        document_type="OFICIO",
        document_month=3,
        document_day=15,
        description="Documento administrativo de prueba.",
    )

    assert document["box_id"] == box["id"]
    assert document["box_type"] == "DOCUMENTOS_ADMINISTRATIVOS"
    assert document["title"] == "Oficio de prueba"
    assert document["document_year"] == 2026
    assert document["lifecycle_status"] == "ACTIVE"

    detail = client.get(f"/api/v1/administrative-documents/{document['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == document["id"]


def test_duplicate_administrative_document_is_rejected(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    create_administrative_document(client, box_id=box["id"], title="Oficio Duplicado")

    response = client.post(
        "/api/v1/administrative-documents",
        json={
            "box_id": box["id"],
            "title": "oficio duplicado",
            "document_year": 2026,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_administrative_document"


def test_list_and_filter_administrative_documents(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    create_administrative_document(
        client,
        box_id=box["id"],
        title="Oficio 2026",
        document_year=2026,
    )
    create_administrative_document(
        client,
        box_id=box["id"],
        title="Oficio 2025",
        document_year=2025,
    )

    response = client.get(
        "/api/v1/administrative-documents",
        params={"box_id": box["id"], "document_year": 2026},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Oficio 2026"


def test_update_administrative_document_and_reject_stale_version(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    document = create_administrative_document(client, box_id=box["id"], title="Original")

    updated = client.patch(
        f"/api/v1/administrative-documents/{document['id']}",
        json={
            "title": "Actualizado",
            "document_month": 4,
            "document_day": 20,
            "notes": "Notas actualizadas",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Actualizado"
    assert updated.json()["document_month"] == 4
    assert updated.json()["document_day"] == 20
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/administrative-documents/{document['id']}",
        json={"title": "Otra vez", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["details"]["reason"] == "stale_version"


def test_administrative_document_rejects_invalid_partial_date(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )

    response = client.post(
        "/api/v1/administrative-documents",
        json={
            "box_id": box["id"],
            "title": "Fecha invalida",
            "document_year": 2026,
            "document_day": 10,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 422


def test_administrative_document_rejects_case_file_box(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    case_box = create_box(client, court_id=court_id, box_type="EXPEDIENTES")

    response = client.post(
        "/api/v1/administrative-documents",
        json={
            "box_id": case_box["id"],
            "title": "Documento invalido",
            "document_year": 2026,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "box_type_mismatch"


def test_administrative_document_duplicates_endpoint(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    document = create_administrative_document(client, box_id=box["id"], title="Duplicable")

    response = client.get(
        "/api/v1/administrative-documents/duplicates",
        params={"box_id": box["id"], "title": "Duplicable", "document_year": 2026},
    )

    assert response.status_code == 200, response.text
    payload = cast(list[dict[str, Any]], response.json())
    assert payload
    assert payload[0]["id"] == document["id"]
    assert payload[0]["match_type"] == "EXACT"


def test_archive_void_and_soft_delete_administrative_document(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    archived = create_administrative_document(client, box_id=box["id"], title="Archivable")
    deleted = create_administrative_document(client, box_id=box["id"], title="Borrable")

    archive_response = client.post(
        f"/api/v1/administrative-documents/{archived['id']}/archive",
        json={"reason": "Archivo de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert archive_response.status_code == 200, archive_response.text
    assert archive_response.json()["lifecycle_status"] == "ARCHIVED"

    void_response = client.post(
        f"/api/v1/administrative-documents/{archived['id']}/void",
        json={"reason": "Anulacion de prueba.", "expected_version": 2},
        headers=csrf_headers(client),
    )
    assert void_response.status_code == 200, void_response.text
    assert void_response.json()["lifecycle_status"] == "VOIDED"

    delete_response = client.request(
        "DELETE",
        f"/api/v1/administrative-documents/{deleted['id']}",
        json={"reason": "Baja logica de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert delete_response.status_code == 204, delete_response.text

    missing = client.get(f"/api/v1/administrative-documents/{deleted['id']}")
    assert missing.status_code == 404


def test_create_administrative_document_in_archived_box_is_rejected(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    archived = client.post(
        f"/api/v1/boxes/{box['id']}/archive",
        json={"reason": "Archivo previo.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert archived.status_code == 200, archived.text

    response = client.post(
        "/api/v1/administrative-documents",
        json={
            "box_id": box["id"],
            "title": "Documento en caja archivada",
            "document_year": 2026,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "box_not_active"


def test_get_missing_administrative_document_returns_not_found(
    seeded_api_client: TestClient,
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get(f"/api/v1/administrative-documents/{uuid4()}")

    assert response.status_code == 404
