"""`FeedRepository` and `CatalogRepository` in memory."""

from copy import deepcopy
from uuid import UUID

from app.domain.feed import Feed, FeedItem, FeedStatus


class InMemoryFeedRepository:
    """Feeds by ID."""

    def __init__(self) -> None:
        self._feeds: dict[UUID, Feed] = {}

    async def add(self, feed: Feed) -> None:
        """Store a new feed."""
        self._feeds[feed.id] = deepcopy(feed)

    async def get(self, feed_id: UUID) -> Feed | None:
        """One feed."""
        feed = self._feeds.get(feed_id)
        return deepcopy(feed) if feed else None

    async def update(self, feed: Feed) -> None:
        """Save the feed."""
        if feed.id in self._feeds:
            self._feeds[feed.id] = deepcopy(feed)

    async def latest(self, profile_id: UUID, done_only: bool = False) -> Feed | None:
        """The profile's newest feed, or its newest finished one."""
        owned = [
            feed
            for feed in self._feeds.values()
            if feed.profile_id == profile_id and (not done_only or feed.status is FeedStatus.DONE)
        ]
        newest = max(owned, key=lambda feed: feed.created_at, default=None)
        return deepcopy(newest) if newest else None


class InMemoryCatalogRepository:
    """Items by ref."""

    def __init__(self) -> None:
        self._items: dict[str, FeedItem] = {}

    async def put_many(self, items: list[FeedItem]) -> None:
        """Store or refresh these items."""
        for item in items:
            self._items[item.ref] = item

    async def get_many(self, refs: list[str]) -> dict[str, FeedItem]:
        """The known items among these refs."""
        return {ref: self._items[ref] for ref in refs if ref in self._items}
