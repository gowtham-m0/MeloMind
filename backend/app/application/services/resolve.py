"""Resolving a favourite the user typed (a name, a song, a lyric they remember) in the background:
the agent climbs the hint ladder and the frontend polls the run.

What was typed lives only in the background job. It's never stored or logged, so a lyric is
never kept (rule 12); proposals hold names only.
"""

import asyncio
import logging
from functools import partial
from typing import Protocol
from uuid import UUID

from app.application.agent.runners import ResolveOutcome
from app.application.ports import AgentRunRepository, ExclusionRepository
from app.application.services.background import BackgroundRunner
from app.application.services.profiles import ProfileService
from app.core.errors import InvalidInputError
from app.domain.feedback import Blocklist
from app.domain.models import FavouriteKind
from app.domain.runs import AgentRun, AgentStep, RunKind, RunStatus, StepLevel

logger = logging.getLogger(__name__)

TEXT_MAX = 300
HINT_MAX = 100
RESOLVE_TIMEOUT_SECONDS = 45.0
NODE = "resolve"


class Resolver(Protocol):
    """Climbs the hint ladder (the agent's resolve_favourite workflow)."""

    async def resolve(
        self,
        run_id: UUID,
        profile_id: UUID,
        blocklist: Blocklist,
        text: str,
        kind: FavouriteKind | None,
        hint: str | None,
    ) -> ResolveOutcome:
        """Proposals, or a question for the user."""
        ...


class ResolveService:
    """Starts resolve runs for their owner's profiles."""

    def __init__(
        self,
        profiles: ProfileService,
        exclusions: ExclusionRepository,
        runs: AgentRunRepository,
        resolver: Resolver,
        runner: BackgroundRunner,
    ) -> None:
        self._profiles = profiles
        self._exclusions = exclusions
        self._runs = runs
        self._resolver = resolver
        self._runner = runner

    async def start(
        self,
        owner_id: UUID,
        profile_id: UUID,
        text: str,
        kind: FavouriteKind | None = None,
        hint: str | None = None,
    ) -> UUID:
        """Start a resolve run and return its ID. Poll it for the proposals."""
        profile = await self._profiles.get(owner_id, profile_id)
        typed = " ".join(text.split())
        if not typed or len(typed) > TEXT_MAX:
            raise InvalidInputError(f"Type 1 to {TEXT_MAX} characters.")
        extra = " ".join((hint or "").split()) or None
        if extra is not None and len(extra) > HINT_MAX:
            raise InvalidInputError(f"Keep the hint under {HINT_MAX} characters.")
        run = AgentRun(profile_id=profile.id, kind=RunKind.RESOLVE)
        await self._runs.add(run)
        await self._runner.spawn(partial(self._execute, run.id, profile.id, typed, kind, extra))
        return run.id

    async def _execute(
        self,
        run_id: UUID,
        profile_id: UUID,
        text: str,
        kind: FavouriteKind | None,
        hint: str | None,
    ) -> None:
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile_id))
        try:
            outcome = await asyncio.wait_for(
                self._resolver.resolve(run_id, profile_id, blocklist, text, kind, hint),
                RESOLVE_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("Resolving a favourite failed: %s", type(exc).__name__)
            await self._runs.append_step(
                run_id,
                AgentStep(
                    node=NODE,
                    message="Couldn't look that up just now. Please try again.",
                    level=StepLevel.WARNING,
                ),
            )
            await self._runs.finish(run_id, RunStatus.FAILED, None)
            return
        if outcome.proposals:
            await self._runs.finish(
                run_id,
                RunStatus.DONE,
                {"proposals": [proposal.to_result() for proposal in outcome.proposals]},
            )
            return
        await self._runs.finish(
            run_id,
            RunStatus.NEEDS_HINT,
            {
                "proposals": [],
                "question": outcome.question,
                "text_favourite": outcome.text_favourite,
            },
        )
