"""Asking the agent for one extra row, in the background: a mood from "Your vibe today", a
surprise, or the user's own words. The frontend polls the run, whose result is the row.

The words guide one run. They're never stored or logged; the log says what they turned into.
"""

import asyncio
import logging
from functools import partial
from typing import Protocol
from uuid import UUID

from app.application.agent.builder import AskRequest
from app.application.agent.log import RunLog
from app.application.agent.types import AskIntent
from app.application.ports import (
    AgentRunRepository,
    CatalogRepository,
    ExclusionRepository,
    FeedRepository,
)
from app.application.services.background import BackgroundRunner
from app.application.services.profiles import ProfileService
from app.application.services.rate_limit import SlidingWindowRateLimiter
from app.core.errors import InvalidInputError
from app.domain.feed import FeedRow
from app.domain.feed_json import row_to_json
from app.domain.feedback import Blocklist
from app.domain.moods import MOODS
from app.domain.runs import AgentRun, RunKind, RunStatus

logger = logging.getLogger(__name__)

TEXT_MAX = 300
# The agent stops at its own limit; this only catches a run that is stuck.
ASK_HARD_TIMEOUT_SECONDS = 60.0
SURPRISE = "surprise"
NODE = "ask"


class Asker(Protocol):
    """Builds the ask row (the agent's ask workflow)."""

    async def ask(self, request: AskRequest) -> FeedRow | None:
        """The row, or None when nothing new was found. Raises when it can't finish."""
        ...


class AskService:
    """Starts ask runs for their owner's profiles. They share the feed's rate limit."""

    def __init__(
        self,
        profiles: ProfileService,
        feeds: FeedRepository,
        runs: AgentRunRepository,
        exclusions: ExclusionRepository,
        catalog: CatalogRepository,
        asker: Asker,
        runner: BackgroundRunner,
        rate_limiter: SlidingWindowRateLimiter,
    ) -> None:
        self._profiles = profiles
        self._feeds = feeds
        self._runs = runs
        self._exclusions = exclusions
        self._catalog = catalog
        self._asker = asker
        self._runner = runner
        self._rate_limiter = rate_limiter

    async def start(
        self,
        owner_id: UUID,
        profile_id: UUID,
        text: str | None = None,
        mood: str | None = None,
        kind: str | None = None,
    ) -> UUID:
        """Start an ask run and return its ID. Poll it for the row. A surprise wins over a
        mood, and a mood over words."""
        profile = await self._profiles.get(owner_id, profile_id)
        intent = _intent(text, mood, kind)
        self._rate_limiter.check(owner_id)
        newest = await self._feeds.latest(profile.id, done_only=True)
        run = AgentRun(profile_id=profile.id, kind=RunKind.ASK)
        await self._runs.add(run)
        request = AskRequest(
            profile=profile,
            run_id=run.id,
            intent=intent,
            previous_refs=frozenset(item.ref for item in newest.items()) if newest else frozenset(),
        )
        await self._runner.spawn(partial(self._execute, request))
        return run.id

    async def _execute(self, request: AskRequest) -> None:
        log = RunLog(self._runs, request.run_id)
        try:
            row = await asyncio.wait_for(self._asker.ask(request), ASK_HARD_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("Asking the agent failed")
            await self._fail(log, "Couldn't build that row just now. Please try again.")
            return
        if row is not None:
            # Something may have been dismissed while the agent worked: check once more (rule 3).
            blocklist = Blocklist.from_exclusions(
                await self._exclusions.list_for_profile(request.profile.id)
            )
            items = tuple(i for i in row.items if not blocklist.blocks(i.ref, i.title))
            row = FeedRow(
                key=row.key,
                title=row.title,
                subtitle=row.subtitle,
                placement=row.placement,
                items=items,
            )
        if row is None or not row.items:
            await self._fail(log, "Nothing new to show for that. Try other words.")
            return
        await self._catalog.put_many(list(row.items))
        await log.info(NODE, f"Row ready: {len(row.items)} picks.")
        await self._runs.finish(request.run_id, RunStatus.DONE, row_to_json(row))

    async def _fail(self, log: RunLog, message: str) -> None:
        await log.warn(NODE, message)
        await self._runs.finish(log.run_id, RunStatus.FAILED, None)


def _intent(text: str | None, mood: str | None, kind: str | None) -> AskIntent:
    """What to ask for, or a 422 when it can't be understood."""
    typed = " ".join((text or "").split())
    if len(typed) > TEXT_MAX:
        raise InvalidInputError(f"Keep your request under {TEXT_MAX} characters.")
    if kind not in (None, SURPRISE):
        raise InvalidInputError("The only kind of ask is “surprise”.")
    if mood is not None and mood not in MOODS:
        raise InvalidInputError(f"Pick a mood: {', '.join(MOODS)}.")
    if kind == SURPRISE:
        return AskIntent(surprise=True)
    if mood is not None:
        return AskIntent(mood=mood)
    if typed:
        return AskIntent(text=typed)
    raise InvalidInputError("Say what you're after, pick a mood, or ask for a surprise.")
