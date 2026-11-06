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
from tests.integration.b7_helpers import active_court_id, create_box, create_case_file

pytestmark = pytest.mark.integration


def test_create_case_file_inside_expediente_box(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id, box_type="EXPEDIENTES")

    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0001",
    )

    assert case_file["box_id"] == box["id"]
    assert case_file["box_type"] == "EXPEDIENTES"
    assert case_file["nuc_normalized"] == "NUC-2026-0001"
    assert case_file["verification_status"] == "PENDING"
    assert any("No hay perfil" in warning for warning in case_file["warnings"])
    assert case_file["parties"] == []


def test_case_file_rejects_administrative_box(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    admin_box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )

    response = client.post(
        "/api/v1/case-files",
        json={
            "court_id": court_id,
            "box_id": admin_box["id"],
            "nuc": "NUC-2026-0002",
            "year": 2026,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "box_type_mismatch"


def test_duplicate_nuc_requires_audited_override(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    create_case_file(client, court_id=court_id, box_id=box["id"], nuc="NUC-2026-0003")

    duplicate = client.post(
        "/api/v1/case-files",
        json={
            "court_id": court_id,
            "box_id": box["id"],
            "nuc": "nuc-2026-0003",
            "year": 2026,
        },
        headers=csrf_headers(client),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["details"]["reason"] == "duplicate_nuc"

    overridden = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="nuc-2026-0003",
        duplicate_override=True,
        duplicate_override_reason="Expediente historico duplicado.",
    )
    assert overridden["verification_status"] == "CONFLICT"
    assert any("duplicado" in warning.lower() for warning in overridden["warnings"])


def test_case_file_duplicates_endpoint(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0004",
    )

    response = client.get(
        "/api/v1/case-files/duplicates",
        params={"court_id": court_id, "nuc": "NUC-2026-0004", "year": 2026},
    )

    assert response.status_code == 200, response.text
    payload = cast(list[dict[str, Any]], response.json())
    assert payload
    assert payload[0]["id"] == case_file["id"]
    assert payload[0]["match_type"] == "EXACT"


def test_list_and_get_case_files(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0005",
    )

    listing = client.get(
        "/api/v1/case-files",
        params={"court_id": court_id, "q": "NUC-2026-0005"},
    )
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == case_file["id"]

    detail = client.get(f"/api/v1/case-files/{case_file['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["nuc_raw"] == "NUC-2026-0005"


def test_update_case_file_and_reject_stale_version(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0006",
    )

    updated = client.patch(
        f"/api/v1/case-files/{case_file['id']}",
        json={
            "description": "Descripcion actualizada",
            "judge_name": "Jueza de prueba",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Descripcion actualizada"
    assert updated.json()["judge_name"] == "Jueza de prueba"
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/case-files/{case_file['id']}",
        json={"description": "Otra", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["details"]["reason"] == "stale_version"


def test_relocate_case_file_between_expediente_boxes(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    origin = create_box(client, court_id=court_id)
    destination = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=origin["id"],
        nuc="NUC-2026-0007",
    )

    relocated = client.post(
        f"/api/v1/case-files/{case_file['id']}/relocate",
        json={
            "box_id": destination["id"],
            "reason": "Reubicacion de prueba.",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )
    assert relocated.status_code == 200, relocated.text
    assert relocated.json()["box_id"] == destination["id"]

    admin_box = create_box(
        client,
        court_id=court_id,
        box_type="DOCUMENTOS_ADMINISTRATIVOS",
    )
    wrong_type = client.post(
        f"/api/v1/case-files/{case_file['id']}/relocate",
        json={
            "box_id": admin_box["id"],
            "reason": "Reubicacion invalida.",
            "expected_version": 2,
        },
        headers=csrf_headers(client),
    )
    assert wrong_type.status_code == 422
    assert wrong_type.json()["error"]["details"]["reason"] == "box_type_mismatch"


def test_archive_void_and_soft_delete_case_file(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    archived = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0008",
    )
    deleted = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-0009",
    )

    archive_response = client.post(
        f"/api/v1/case-files/{archived['id']}/archive",
        json={"reason": "Archivo de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert archive_response.status_code == 200, archive_response.text
    assert archive_response.json()["lifecycle_status"] == "ARCHIVED"

    void_response = client.post(
        f"/api/v1/case-files/{archived['id']}/void",
        json={"reason": "Anulacion de prueba.", "expected_version": 2},
        headers=csrf_headers(client),
    )
    assert void_response.status_code == 200, void_response.text
    assert void_response.json()["lifecycle_status"] == "VOIDED"

    delete_response = client.request(
        "DELETE",
        f"/api/v1/case-files/{deleted['id']}",
        json={"reason": "Baja logica de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert delete_response.status_code == 204, delete_response.text

    missing = client.get(f"/api/v1/case-files/{deleted['id']}")
    assert missing.status_code == 404


def test_get_missing_case_file_returns_not_found(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get(f"/api/v1/case-files/{uuid4()}")

    assert response.status_code == 404
