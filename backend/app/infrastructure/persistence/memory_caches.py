"""The media and Qloo caches in memory. They last until the process stops."""

from copy import deepcopy
from typing import Any

from app.application.ports import MediaCacheEntry, PlayableMedia, QlooCacheEntry
from app.domain.models import utc_now


class InMemoryMediaCache:
    """Media lookups by query key."""

    def __init__(self) -> None:
        self._entries: dict[str, MediaCacheEntry] = {}

    async def get(self, query_key: str) -> MediaCacheEntry | None:
        """The cached lookup, or None."""
        return self._entries.get(query_key)

    async def put(self, query_key: str, media: PlayableMedia | None) -> None:
        """Remember a lookup's result."""
        self._entries[query_key] = MediaCacheEntry(media=media, cached_at=utc_now())


class InMemoryQlooCache:
    """Parsed Qloo results by cache key."""

    def __init__(self) -> None:
        self._entries: dict[str, QlooCacheEntry] = {}

    async def get(self, cache_key: str) -> QlooCacheEntry | None:
        """The cached results, or None."""
        entry = self._entries.get(cache_key)
        return deepcopy(entry) if entry else None

    async def put(self, cache_key: str, rows: list[dict[str, Any]]) -> None:
        """Remember the results."""
        self._entries[cache_key] = QlooCacheEntry(rows=deepcopy(rows), cached_at=utc_now())
