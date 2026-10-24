"""Use cases for the feed: the latest snapshot, building a new one in the background, and
keeping the snapshot honest when feedback arrives (stale flag, instant removal)."""

import asyncio
import logging
from datetime import timedelta
from functools import partial
from typing import Protocol
from uuid import UUID

from app.application.agent.builder import FeedRequest, FeedResult
from app.application.agent.log import RunLog
from app.application.ports import (
    AgentRunRepository,
    CatalogRepository,
    ExclusionRepository,
    FeedRepository,
)
from app.application.services.background import BackgroundRunner
from app.application.services.profiles import ProfileService
from app.application.services.rate_limit import SlidingWindowRateLimiter
from app.core.errors import NotFoundError
from app.domain.feed import Feed, FeedRow, FeedStatus
from app.domain.feedback import Blocklist
from app.domain.models import utc_now
from app.domain.runs import AgentRun, RunKind, RunStatus

logger = logging.getLogger(__name__)

# A build that takes longer than this is stuck: the agent itself stops at 25 seconds.
BUILD_HARD_TIMEOUT_SECONDS = 90.0
STUCK_AFTER = timedelta(seconds=BUILD_HARD_TIMEOUT_SECONDS * 2)
NODE = "feed"


class FeedBuilder(Protocol):
    """Builds one feed (the agent's build_feed workflow)."""

    async def build(self, request: FeedRequest) -> FeedResult:
        """The finished feed. Raises when building can't finish."""
        ...


class FeedService:
    """Feeds for their owner only: someone else's profile is reported as not found."""

    def __init__(
        self,
        profiles: ProfileService,
        feeds: FeedRepository,
        runs: AgentRunRepository,
        exclusions: ExclusionRepository,
        catalog: CatalogRepository,
        builder: FeedBuilder,
        runner: BackgroundRunner,
        rate_limiter: SlidingWindowRateLimiter,
    ) -> None:
        self._profiles = profiles
        self._feeds = feeds
        self._runs = runs
        self._exclusions = exclusions
        self._catalog = catalog
        self._builder = builder
        self._runner = runner
        self._rate_limiter = rate_limiter

    async def latest(self, owner_id: UUID, profile_id: UUID) -> Feed:
        """The newest finished feed. Not found when there is none yet."""
        await self._profiles.get(owner_id, profile_id)
        feed = await self._feeds.latest(profile_id, done_only=True)
        if feed is None:
            raise NotFoundError("No feed yet. Start one with refresh.")
        return feed

    async def refresh(
        self, owner_id: UUID, profile_id: UUID, *, count_towards_limit: bool = True
    ) -> Feed:
        """Start building a new feed in the background, or return the one already building."""
        profile = await self._profiles.get(owner_id, profile_id)
        newest = await self._feeds.latest(profile.id)
        if (
            newest is not None
            and newest.status is FeedStatus.BUILDING
            and utc_now() - newest.created_at < STUCK_AFTER
        ):
            return newest
        if count_towards_limit:
            self._rate_limiter.check(owner_id)
        previous = await self._feeds.latest(profile.id, done_only=True)
        run = AgentRun(profile_id=profile.id, kind=RunKind.FEED)
        feed = Feed(profile_id=profile.id, agent_run_id=run.id)
        await self._runs.add(run)
        await self._feeds.add(feed)
        request = FeedRequest(
            profile=profile,
            run_id=run.id,
            previous_refs=frozenset(item.ref for item in previous.items())
            if previous
            else frozenset(),
            previous_tags=previous.taste_tags if previous else (),
        )
        await self._runner.spawn(partial(self._execute, feed.id, request))
        return feed

    async def mark_stale(self, profile_id: UUID) -> bool:
        """Flag the newest finished feed as out of date. True when there was one."""
        feed = await self._feeds.latest(profile_id, done_only=True)
        if feed is None or feed.stale:
            return feed is not None
        feed.stale = True
        await self._feeds.update(feed)
        return True

    async def remove_item(self, profile_id: UUID, ref: str) -> None:
        """Take an item out of the newest feed at once ("not interested")."""
        feed = await self._feeds.latest(profile_id, done_only=True)
        if feed is not None and feed.without(ref):
            await self._feeds.update(feed)

    async def _execute(self, feed_id: UUID, request: FeedRequest) -> None:
        """The background part of `refresh`: run the agent and store the feed."""
        log = RunLog(self._runs, request.run_id)
        try:
            result = await asyncio.wait_for(
                self._builder.build(request), BUILD_HARD_TIMEOUT_SECONDS
            )
        except Exception:
            logger.exception("Building the feed failed")
            await self._fail(feed_id, log, "Building your feed failed. Please try again.")
            return
        feed = await self._feeds.get(feed_id)
        if feed is None:
            return
        # Something may have been dismissed while the agent worked: check once more (rule 3).
        blocklist = Blocklist.from_exclusions(
            await self._exclusions.list_for_profile(request.profile.id)
        )
        rows = [
            FeedRow(
                key=row.key,
                title=row.title,
                subtitle=row.subtitle,
                placement=row.placement,
                items=tuple(i for i in row.items if not blocklist.blocks(i.ref, i.title)),
            )
            for row in result.rows
        ]
        hero = result.hero
        if hero is not None and blocklist.blocks(hero.ref, hero.title):
            hero = None
        feed.hero = hero
        feed.rows = [row for row in rows if row.items]
        feed.summary = result.summary
        feed.taste_tags = result.taste_tags
        if not feed.items():
            await self._fail(
                feed_id, log, "Nothing to show yet. Add a few favourites and try again."
            )
            return
        feed.status = FeedStatus.DONE
        await self._feeds.update(feed)
        await self._catalog.put_many(feed.items())
        await log.info(NODE, f"Feed ready: {len(feed.items())} picks in {len(feed.rows)} rows.")
        await self._runs.finish(
            request.run_id, RunStatus.DONE, {"feed_id": str(feed_id), **result.run_summary}
        )

    async def _fail(self, feed_id: UUID, log: RunLog, message: str) -> None:
        feed = await self._feeds.get(feed_id)
        if feed is not None:
            feed.status = FeedStatus.FAILED
            await self._feeds.update(feed)
        await log.warn(NODE, message)
        await self._runs.finish(log.run_id, RunStatus.FAILED, {"feed_id": str(feed_id)})
