"""Shared fixtures: a test signing key standing in for Supabase's JWKS, and an API client."""

import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.api.auth import SupabaseTokenVerifier
from app.api.deps import Container, get_container, wire
from app.core.settings import Settings
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from app.main import create_app

ISSUER = "https://test-project.supabase.co/auth/v1"
KEY_ID = "test-key"

_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_PUBLIC_JWK = jwt.PyJWK(
    {**jwt.algorithms.ECAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True), "kid": KEY_ID},
    algorithm="ES256",
)

TokenFactory = Callable[..., str]
AuthHeaders = Callable[[UUID], dict[str, str]]


class FakeSigningKeys:
    """Plays the project's JWKS: knows one public key, and rejects tokens with another `kid`."""

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        if jwt.get_unverified_header(token).get("kid") != KEY_ID:
            raise jwt.PyJWKClientError("Unable to find a signing key that matches")
        return _PUBLIC_JWK


def make_token(user_id: UUID, **overrides: Any) -> str:
    """A token like Supabase issues, signed with the test key. Overrides change claims."""
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": now + 3600,
        "iat": now,
        "role": "authenticated",
        "is_anonymous": True,
    }
    claims.update(overrides)
    claims = {key: value for key, value in claims.items() if value is not None}
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256", headers={"kid": KEY_ID})


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only."""
    return "asyncio"


@pytest.fixture
def verifier() -> SupabaseTokenVerifier:
    """A verifier that trusts the test key."""
    return SupabaseTokenVerifier(FakeSigningKeys(), issuer=ISSUER)


@pytest.fixture
def container(verifier: SupabaseTokenVerifier) -> Container:
    """Services over the demo fixtures and in-memory storage."""
    return wire(FixtureTasteGraph(), InMemoryProfileRepository(), verifier, load_demo_profiles())


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    """An API client whose app uses the test container."""
    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth() -> AuthHeaders:
    """Authorization headers for a user."""
    return lambda user_id: {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture
def user_id() -> UUID:
    """A fresh signed-in user."""
    return uuid4()
