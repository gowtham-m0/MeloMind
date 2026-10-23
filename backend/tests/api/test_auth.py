"""API tests for sign-in: every route except health needs a valid Supabase token."""

import time
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_container, wire
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.conftest import make_token

PROFILES = "/api/v1/profiles"


def test_valid_token_is_accepted(client: TestClient, user_id: UUID) -> None:
    response = client.get(PROFILES, headers={"Authorization": f"Bearer {make_token(user_id)}"})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        PROFILES,
        "/api/v1/taste/search?q=abba",
        "/api/v1/profiles/00000000-0000-0000-0000-000000000000",
    ],
)
def test_missing_token_is_401(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_seed_without_token_is_401(client: TestClient) -> None:
    assert client.post("/api/v1/demo/seed").status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},
        {"aud": "anon"},
        {"iss": "https://someone-else.supabase.co/auth/v1"},
        {"exp": None},
        {"sub": "not-a-uuid"},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "no-expiry", "bad-subject"],
)
def test_invalid_tokens_are_401(client: TestClient, user_id: UUID, overrides: dict) -> None:
    token = make_token(user_id, **overrides)

    response = client.get(PROFILES, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_token_issued_slightly_in_the_future_is_accepted(client: TestClient, user_id: UUID) -> None:
    # Supabase's clock can be a second or two ahead of the backend's.
    token = make_token(user_id, iat=int(time.time()) + 5)

    response = client.get(PROFILES, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_garbage_token_is_401(client: TestClient) -> None:
    response = client.get(PROFILES, headers={"Authorization": "Bearer not.a.token"})

    assert response.status_code == 401


def test_without_supabase_configured_every_request_is_401(
    client: TestClient, user_id: UUID
) -> None:
    unconfigured = wire(
        FixtureTasteGraph(), InMemoryProfileRepository(), None, load_demo_profiles()
    )
    client.app.dependency_overrides[get_container] = lambda: unconfigured  # type: ignore[attr-defined]

    response = client.get(PROFILES, headers={"Authorization": f"Bearer {make_token(user_id)}"})

    assert response.status_code == 401
    assert "SUPABASE_URL" in response.json()["detail"]
