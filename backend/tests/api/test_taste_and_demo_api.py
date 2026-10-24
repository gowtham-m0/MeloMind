"""API tests for taste search and the demo seed."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from tests.conftest import AuthHeaders

SEARCH = "/api/v1/taste/search"
SEED = "/api/v1/demo/seed"


def test_search_returns_matches_with_type_and_year(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    response = client.get(
        SEARCH, params={"q": "To Kill a Mockingbird", "type": "book"}, headers=auth(user_id)
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "entity_id": "demo-book-to-kill-a-mockingbird",
            "name": "To Kill a Mockingbird",
            "type": "book",
            "release_year": 1960,
            "image_url": None,
        }
    ]


def test_song_search_finds_the_singer(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    response = client.get(
        SEARCH, params={"q": "temptations", "type": "song"}, headers=auth(user_id)
    )

    assert [match["type"] for match in response.json()] == ["artist"]


def test_search_validation(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)

    assert client.get(SEARCH, params={"q": ""}, headers=headers).status_code == 422
    assert client.get(SEARCH, params={"q": "   "}, headers=headers).status_code == 422
    assert (
        client.get(SEARCH, params={"q": "x", "type": "song_title"}, headers=headers).status_code
        == 422
    )


def test_demo_seed_is_idempotent_and_private(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    first = client.post(SEED, headers=auth(user_id))
    second = client.post(SEED, headers=auth(user_id))

    assert first.status_code == 200
    assert first.json() == second.json()
    profiles = client.get("/api/v1/profiles", headers=auth(user_id)).json()
    assert [profile["display_name"] for profile in profiles] == ["Aanya", "Leo"]
    assert [profile["id"] for profile in profiles] == first.json()["profile_ids"]
    assert all(profile["is_demo"] for profile in profiles)
    assert all(fav["verified"] for profile in profiles for fav in profile["favourites"])

    stranger = auth(uuid4())
    assert client.get(f"/api/v1/profiles/{profiles[0]['id']}", headers=stranger).status_code == 404
