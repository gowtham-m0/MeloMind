"""A `MediaResolver` that caches every lookup in `media_cache`, to save YouTube quota."""

from datetime import timedelta

from app.application.ports import MediaCacheRepository, MediaResolver, PlayableMedia
from app.domain.models import utc_now

QUERY_KEY_MAX = 300
# "Nothing playable" is looked up again after a day, in case a video has appeared.
MISS_TTL = timedelta(days=1)


def query_key(query: str) -> str:
    """The cache key for a query: lower case, single spaces."""
    return " ".join(query.casefold().split())[:QUERY_KEY_MAX]


class CachedMediaResolver:
    """Answers from the cache when it can. Service failures are never cached."""

    def __init__(
        self, inner: MediaResolver, cache: MediaCacheRepository, miss_ttl: timedelta = MISS_TTL
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._miss_ttl = miss_ttl

    async def resolve(self, query: str) -> PlayableMedia | None:
        """The cached result, or a fresh lookup that is then cached."""
        key = query_key(query)
        entry = await self._cache.get(key)
        if entry is not None and (
            entry.media is not None or utc_now() - entry.cached_at < self._miss_ttl
        ):
            return entry.media
        media = await self._inner.resolve(query)
        await self._cache.put(key, media)
        return media
