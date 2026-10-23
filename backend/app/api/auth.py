"""Verifies Supabase access tokens against the project's public signing keys (JWKS)."""

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import jwt

from app.core.errors import UnauthorizedError

AUDIENCE = "authenticated"
# Supabase's asymmetric signing keys. Legacy HS256 tokens are not accepted.
ALGORITHMS = ["ES256", "RS256"]
JWKS_CACHE_SECONDS = 3600
# Supabase's clock can run a little ahead of ours, so a token used straight after sign-in would
# otherwise fail the `iat` check as "not yet valid".
CLOCK_SKEW_SECONDS = 30


@dataclass(frozen=True)
class CurrentUser:
    """The signed-in user. Anonymous demo users are ordinary users."""

    id: UUID
    is_anonymous: bool


class SigningKeySource(Protocol):
    """Finds the public key a token was signed with (PyJWT's `PyJWKClient`, or a test fake)."""

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        """The key matching the token's `kid`."""
        ...


class SupabaseTokenVerifier:
    """Checks a token's signature, `exp`, `iss` and `aud`, and returns who it belongs to."""

    def __init__(self, keys: SigningKeySource, issuer: str) -> None:
        self._keys = keys
        self._issuer = issuer

    @classmethod
    def for_project(cls, supabase_url: str) -> "SupabaseTokenVerifier":
        """A verifier for one Supabase project, fetching and caching its JWKS."""
        base = supabase_url.rstrip("/")
        keys = jwt.PyJWKClient(
            f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=JWKS_CACHE_SECONDS
        )
        return cls(keys, issuer=f"{base}/auth/v1")

    async def verify(self, token: str) -> CurrentUser:
        """The token's user. Raises `UnauthorizedError` for any invalid or expired token."""
        try:
            # PyJWKClient fetches the JWKS over blocking HTTP, so run it off the event loop.
            key = await asyncio.to_thread(self._keys.get_signing_key_from_jwt, token)
            claims: dict[str, Any] = jwt.decode(
                token,
                key.key,
                algorithms=ALGORITHMS,
                audience=AUDIENCE,
                issuer=self._issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            user_id = UUID(str(claims["sub"]))
        except (jwt.PyJWTError, ValueError) as exc:
            raise UnauthorizedError(
                "Your sign-in isn't valid or has expired. Please sign in again."
            ) from exc
        return CurrentUser(id=user_id, is_anonymous=bool(claims.get("is_anonymous", False)))
