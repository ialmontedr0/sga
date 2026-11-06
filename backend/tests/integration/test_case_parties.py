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
from tests.integration.b7_helpers import (
    active_court_id,
    create_box,
    create_case_file,
    party_role_id,
)

pytestmark = pytest.mark.integration


def _add_party_with_person(
    client: TestClient,
    *,
    case_file_id: str,
    role_id: str,
    display_name: str,
    identification_number: str | None = None,
    is_primary: bool = False,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "person": {
            "display_name": display_name,
            "identification_type": "CEDULA",
            "identification_number": identification_number,
        },
        "party_role_id": role_id,
        "is_primary": is_primary,
    }
    response = client.post(
        f"/api/v1/case-files/{case_file_id}/parties/with-person",
        json=payload,
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_add_party_with_person_and_list_parties(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1001",
    )

    party = _add_party_with_person(
        client,
        case_file_id=case_file["id"],
        role_id=role_id,
        display_name="  Ana   Perez ",
        identification_number="001-1234567-8",
        is_primary=True,
    )

    assert party["person"]["display_name"] == "Ana Perez"
    assert party["person"]["normalized_name"] == "ANAPEREZ"
    assert party["party_role_code"] == "IMPUTADO"
    assert party["is_primary"] is True

    listing = client.get(f"/api/v1/case-files/{case_file['id']}/parties")
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    assert listing.json()[0]["person"]["id"] == party["person"]["id"]


def test_duplicate_party_relation_is_rejected(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1002",
    )
    party = _add_party_with_person(
        client,
        case_file_id=case_file["id"],
        role_id=role_id,
        display_name="Persona Duplicada",
    )

    response = client.post(
        f"/api/v1/case-files/{case_file['id']}/parties",
        json={
            "person_id": party["person"]["id"],
            "party_role_id": role_id,
            "is_primary": False,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_case_party"


def test_second_primary_party_is_rejected(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1003",
    )
    _add_party_with_person(
        client,
        case_file_id=case_file["id"],
        role_id=role_id,
        display_name="Primera Persona",
        is_primary=True,
    )

    response = client.post(
        f"/api/v1/case-files/{case_file['id']}/parties/with-person",
        json={
            "person": {"display_name": "Segunda Persona"},
            "party_role_id": role_id,
            "is_primary": True,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "primary_party_exists"


def test_add_existing_person_to_second_case_and_remove(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    first = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1004",
    )
    second = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1005",
    )
    party = _add_party_with_person(
        client,
        case_file_id=first["id"],
        role_id=role_id,
        display_name="Persona Compartida",
        identification_number="001-7654321-0",
    )

    added = client.post(
        f"/api/v1/case-files/{second['id']}/parties",
        json={
            "person_id": party["person"]["id"],
            "party_role_id": role_id,
            "is_primary": False,
        },
        headers=csrf_headers(client),
    )
    assert added.status_code == 200, added.text

    removed = client.request(
        "DELETE",
        f"/api/v1/case-files/{second['id']}/parties/{added.json()['id']}",
        headers=csrf_headers(client),
    )
    assert removed.status_code == 204, removed.text

    listing = client.get(f"/api/v1/case-files/{second['id']}/parties")
    assert listing.status_code == 200
    assert listing.json() == []


def test_duplicate_person_identification_is_rejected(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    first = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1006",
    )
    second = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1007",
    )
    _add_party_with_person(
        client,
        case_file_id=first["id"],
        role_id=role_id,
        display_name="Persona Original",
        identification_number="001-1111111-1",
    )

    response = client.post(
        f"/api/v1/case-files/{second['id']}/parties/with-person",
        json={
            "person": {
                "display_name": "Persona Nueva",
                "identification_number": "001-1111111-1",
            },
            "party_role_id": role_id,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_person"


def test_person_search_and_duplicates(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    role_id = party_role_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-1008",
    )
    party = _add_party_with_person(
        client,
        case_file_id=case_file["id"],
        role_id=role_id,
        display_name="Jose Maria Nunez",
        identification_number="001-2222222-2",
    )

    listing = client.get("/api/v1/persons", params={"q": "JOSEMARIA"})
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == party["person"]["id"]

    duplicates = client.get(
        "/api/v1/persons/duplicates",
        params={
            "display_name": "Jose Maria Nunez",
            "identification_number": "001-2222222-2",
        },
    )
    assert duplicates.status_code == 200, duplicates.text
    payload = cast(list[dict[str, Any]], duplicates.json())
    assert payload
    assert payload[0]["match_type"] == "IDENTIFICATION"
