"""API tests for profiles and favourites: CRUD, validation, ownership and cascading deletes."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthHeaders

PROFILES = "/api/v1/profiles"


def create_profile(client: TestClient, headers: dict[str, str], **fields: Any) -> dict[str, Any]:
    body = {"display_name": "Margaret", "birth_year": 1948, **fields}
    response = client.post(PROFILES, json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_with_only_name_and_birth_year(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    profile = create_profile(client, auth(user_id))

    assert profile["display_name"] == "Margaret"
    assert profile["birth_year"] == 1948
    assert profile["country_code"] is None
    assert profile["places_lived"] == []
    assert profile["languages"] == []
    assert profile["is_demo"] is False
    assert profile["favourites"] == []


def test_profile_crud(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    profile = create_profile(client, headers, country_code="us", places_lived=["Chicago"])
    url = f"{PROFILES}/{profile['id']}"

    assert client.get(PROFILES, headers=headers).json() == [profile]
    assert client.get(url, headers=headers).json() == profile
    assert profile["country_code"] == "US"

    patched = client.patch(
        url, json={"languages": ["English"], "country_code": None}, headers=headers
    )
    assert patched.status_code == 200
    assert patched.json()["languages"] == ["English"]
    assert patched.json()["country_code"] is None
    assert patched.json()["places_lived"] == ["Chicago"]

    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404
    assert client.get(PROFILES, headers=headers).json() == []


@pytest.mark.parametrize(
    "body",
    [
        {"display_name": "Margaret", "birth_year": 1899},
        {"display_name": "Margaret", "birth_year": 9999},
        {"display_name": "   ", "birth_year": 1948},
        {"birth_year": 1948},
        {"display_name": "Margaret", "birth_year": 1948, "country_code": "USA"},
    ],
)
def test_create_validation(
    client: TestClient, auth: AuthHeaders, user_id: UUID, body: dict[str, Any]
) -> None:
    response = client.post(PROFILES, json=body, headers=auth(user_id))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "body", [{"display_name": None}, {"birth_year": 9999}, {"birth_year": 1899}]
)
def test_patch_validation(
    client: TestClient, auth: AuthHeaders, user_id: UUID, body: dict[str, Any]
) -> None:
    profile = create_profile(client, auth(user_id))

    response = client.patch(f"{PROFILES}/{profile['id']}", json=body, headers=auth(user_id))

    assert response.status_code == 422


def test_other_users_get_404_everywhere(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    profile = create_profile(client, auth(user_id))
    favourite = client.post(
        f"{PROFILES}/{profile['id']}/favourites",
        json={"name": "The Supremes", "kind": "artist"},
        headers=auth(user_id),
    ).json()
    stranger = auth(uuid4())
    url = f"{PROFILES}/{profile['id']}"

    responses = [
        client.get(url, headers=stranger),
        client.patch(url, json={"display_name": "Mallory"}, headers=stranger),
        client.delete(url, headers=stranger),
        client.post(f"{url}/favourites", json={"name": "X", "kind": "artist"}, headers=stranger),
        client.delete(f"{url}/favourites/{favourite['id']}", headers=stranger),
    ]

    assert [response.status_code for response in responses] == [404] * 5
    assert responses[0].json() == {"error": "not_found", "detail": "Profile not found."}
    assert client.get(PROFILES, headers=stranger).json() == []
    assert client.get(url, headers=auth(user_id)).json()["display_name"] == "Margaret"


def test_favourites_verified_text_and_song(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile = create_profile(client, headers)
    url = f"{PROFILES}/{profile['id']}/favourites"

    verified = client.post(
        url,
        json={"name": "The Supremes", "kind": "artist", "entity_id": "demo-artist-the-supremes"},
        headers=headers,
    )
    text = client.post(url, json={"name": "Grandad's tune", "kind": "artist"}, headers=headers)
    song = client.post(
        url,
        json={
            "name": "The Temptations",
            "kind": "song",
            "entity_id": "demo-artist-the-temptations",
            "song_title": "My Girl",
        },
        headers=headers,
    )

    assert verified.status_code == 201
    assert verified.json()["verified"] is True
    assert verified.json()["qloo_id"] == "demo-artist-the-supremes"
    assert text.json()["verified"] is False
    assert text.json()["qloo_id"] is None
    assert song.json()["song_title"] == "My Girl"
    saved = client.get(f"{PROFILES}/{profile['id']}", headers=headers).json()["favourites"]
    assert [favourite["name"] for favourite in saved] == [
        "The Supremes",
        "Grandad's tune",
        "The Temptations",
    ]


def test_song_title_is_rejected_for_other_kinds(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    profile = create_profile(client, auth(user_id))

    response = client.post(
        f"{PROFILES}/{profile['id']}/favourites",
        json={"name": "The Supremes", "kind": "artist", "song_title": "Baby Love"},
        headers=auth(user_id),
    )

    assert response.status_code == 422


def test_remove_favourite(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    profile = create_profile(client, headers)
    url = f"{PROFILES}/{profile['id']}/favourites"
    favourite = client.post(url, json={"name": "Abba", "kind": "artist"}, headers=headers).json()

    assert client.delete(f"{url}/{favourite['id']}", headers=headers).status_code == 204
    assert client.delete(f"{url}/{favourite['id']}", headers=headers).status_code == 404
    assert client.get(f"{PROFILES}/{profile['id']}", headers=headers).json()["favourites"] == []


def test_deleting_a_profile_deletes_its_favourites(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile = create_profile(client, headers)
    url = f"{PROFILES}/{profile['id']}"
    favourite = client.post(
        f"{url}/favourites", json={"name": "Abba", "kind": "artist"}, headers=headers
    ).json()

    assert client.delete(url, headers=headers).status_code == 204

    assert client.delete(f"{url}/favourites/{favourite['id']}", headers=headers).status_code == 404
    assert client.get(PROFILES, headers=headers).json() == []
