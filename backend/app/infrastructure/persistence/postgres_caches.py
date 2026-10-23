"""The media and Qloo caches on Postgres (`media_cache`, `qloo_cache`)."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports import MediaCacheEntry, PlayableMedia, QlooCacheEntry
from app.domain.models import utc_now
from app.infrastructure.persistence.models import MediaCacheRow, QlooCacheRow


class PostgresMediaCache:
    """Media lookups by query key."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get(self, query_key: str) -> MediaCacheEntry | None:
        """The cached lookup, or None."""
        async with self._sessions() as db:
            row = await db.get(MediaCacheRow, query_key)
        if row is None:
            return None
        media = None
        if row.provider and row.video_id and row.duration_s is not None:
            media = PlayableMedia(
                video_id=row.video_id,
                title=row.title or "",
                duration_s=row.duration_s,
                provider="demo" if row.provider == "demo" else "youtube",
            )
        return MediaCacheEntry(media=media, cached_at=row.cached_at)

    async def put(self, query_key: str, media: PlayableMedia | None) -> None:
        """Remember a lookup's result, replacing an older one."""
        async with self._sessions() as db, db.begin():
            await db.merge(
                MediaCacheRow(
                    query_key=query_key,
                    provider=media.provider if media else None,
                    video_id=media.video_id if media else None,
                    title=media.title if media else None,
                    duration_s=media.duration_s if media else None,
                    cached_at=utc_now(),
                )
            )


class PostgresQlooCache:
    """Parsed Qloo results by cache key."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get(self, cache_key: str) -> QlooCacheEntry | None:
        """The cached results, or None."""
        async with self._sessions() as db:
            row = await db.get(QlooCacheRow, cache_key)
        return QlooCacheEntry(rows=row.rows, cached_at=row.cached_at) if row else None

    async def put(self, cache_key: str, rows: list[dict[str, Any]]) -> None:
        """Remember the results, replacing older ones."""
        async with self._sessions() as db, db.begin():
            await db.merge(QlooCacheRow(cache_key=cache_key, rows=rows, cached_at=utc_now()))
