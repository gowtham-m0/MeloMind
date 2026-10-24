"""`FeedRepository` and `CatalogRepository` on Postgres (`feeds`, `catalog_items`)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.feed import Feed, FeedItem, FeedStatus
from app.domain.models import utc_now
from app.infrastructure.persistence.feed_json import (
    item_from_json,
    item_to_json,
    row_from_json,
    row_to_json,
)
from app.infrastructure.persistence.models import CatalogItemRow, FeedRowRecord


def _to_domain(row: FeedRowRecord) -> Feed:
    return Feed(
        id=row.id,
        profile_id=row.profile_id,
        agent_run_id=row.agent_run_id,
        status=FeedStatus(row.status),
        stale=row.stale,
        hero=item_from_json(row.hero) if row.hero else None,
        rows=[row_from_json(data) for data in row.rows],
        summary=row.summary,
        taste_tags=tuple(row.taste_tags),
        created_at=row.created_at,
    )


def _fill(row: FeedRowRecord, feed: Feed) -> None:
    row.status = feed.status.value
    row.stale = feed.stale
    row.hero = item_to_json(feed.hero) if feed.hero else None
    row.rows = [row_to_json(feed_row) for feed_row in feed.rows]
    row.summary = feed.summary
    row.taste_tags = list(feed.taste_tags)


class PostgresFeedRepository:
    """Feed snapshots in Postgres. The database deletes them with their profile."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, feed: Feed) -> None:
        """Store a new feed."""
        row = FeedRowRecord(
            id=feed.id,
            profile_id=feed.profile_id,
            agent_run_id=feed.agent_run_id,
            created_at=feed.created_at,
        )
        _fill(row, feed)
        async with self._sessions() as db, db.begin():
            db.add(row)

    async def get(self, feed_id: UUID) -> Feed | None:
        """One feed."""
        async with self._sessions() as db:
            row = await db.get(FeedRowRecord, feed_id)
            return _to_domain(row) if row else None

    async def update(self, feed: Feed) -> None:
        """Save the feed's status, items and flags."""
        async with self._sessions() as db, db.begin():
            row = await db.get(FeedRowRecord, feed.id)
            if row is not None:
                _fill(row, feed)

    async def latest(self, profile_id: UUID, done_only: bool = False) -> Feed | None:
        """The profile's newest feed, or its newest finished one."""
        query = select(FeedRowRecord).where(FeedRowRecord.profile_id == profile_id)
        if done_only:
            query = query.where(FeedRowRecord.status == FeedStatus.DONE.value)
        query = query.order_by(FeedRowRecord.created_at.desc()).limit(1)
        async with self._sessions() as db:
            row = await db.scalar(query)
            return _to_domain(row) if row else None


class PostgresCatalogRepository:
    """Items by ref in Postgres."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def put_many(self, items: list[FeedItem]) -> None:
        """Store or refresh these items."""
        unique = {item.ref: item for item in items}
        if not unique:
            return
        now = utc_now()
        statement = insert(CatalogItemRow).values(
            [
                {"ref": ref, "data": item_to_json(item), "updated_at": now}
                for ref, item in unique.items()
            ]
        )
        statement = statement.on_conflict_do_update(
            index_elements=[CatalogItemRow.ref],
            set_={"data": statement.excluded.data, "updated_at": statement.excluded.updated_at},
        )
        async with self._sessions() as db, db.begin():
            await db.execute(statement)

    async def get_many(self, refs: list[str]) -> dict[str, FeedItem]:
        """The known items among these refs."""
        if not refs:
            return {}
        async with self._sessions() as db:
            rows = await db.scalars(select(CatalogItemRow).where(CatalogItemRow.ref.in_(refs)))
            return {row.ref: item_from_json(row.data) for row in rows}
