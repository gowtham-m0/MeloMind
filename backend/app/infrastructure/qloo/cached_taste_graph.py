"""A `TasteGraph` that keeps parsed Qloo results in `qloo_cache`, on the server only."""

import hashlib
import json
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from app.application.ports import (
    EntityMatch,
    InsightsQuery,
    QlooCacheRepository,
    TagMatch,
    TasteGraph,
    TasteSource,
)
from app.domain.models import EntityType, utc_now

CACHE_TTL = timedelta(days=1)
# Bumped when the parsed shape changes, so older cached rows (without images) are ignored.
CACHE_VERSION = 2


def cache_key(*parts: Any) -> str:
    """A short, stable key for a request: the SHA-256 of its JSON form."""
    text = json.dumps((CACHE_VERSION, *parts), sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _match_to_row(match: EntityMatch) -> dict[str, Any]:
    row = asdict(match)
    row["type"] = match.type.value
    return row


def _row_to_match(row: dict[str, Any]) -> EntityMatch:
    return EntityMatch(
        **{**row, "type": EntityType(row["type"]), "tags": tuple(row.get("tags") or ())}
    )


class CachedTasteGraph:
    """Answers repeated searches, insights and tag lookups from the cache for a day."""

    def __init__(
        self, inner: TasteGraph, cache: QlooCacheRepository, ttl: timedelta = CACHE_TTL
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl

    @property
    def source(self) -> TasteSource:
        """The wrapped graph's source."""
        return self._inner.source

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        """Cached `search`."""
        key = cache_key("search", query.casefold(), sorted(types), take)
        rows = await self._cached(key)
        if rows is not None:
            return [_row_to_match(row) for row in rows]
        matches = await self._inner.search(query, types, take)
        await self._cache.put(key, [_match_to_row(match) for match in matches])
        return matches

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        """Cached `insights`."""
        key = cache_key("insights", asdict(query))
        rows = await self._cached(key)
        if rows is not None:
            return [_row_to_match(row) for row in rows]
        matches = await self._inner.insights(query)
        await self._cache.put(key, [_match_to_row(match) for match in matches])
        return matches

    async def tags(self, query: str, take: int = 5) -> list[TagMatch]:
        """Cached `tags`."""
        key = cache_key("tags", query.casefold(), take)
        rows = await self._cached(key)
        if rows is not None:
            return [TagMatch(**row) for row in rows]
        tags = await self._inner.tags(query, take)
        await self._cache.put(key, [asdict(tag) for tag in tags])
        return tags

    async def _cached(self, key: str) -> list[dict[str, Any]] | None:
        entry = await self._cache.get(key)
        if entry is None or utc_now() - entry.cached_at > self._ttl:
            return None
        return entry.rows
