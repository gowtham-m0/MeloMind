"""Taste match: compare one profile's taste with another of the owner's profiles, or with a
friend's favourites, and build the "For you both" row."""

import asyncio
import logging
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.application.agent.builder import MatchRequest
from app.application.agent.log import RunLog
from app.application.agent.taste_match import MatchResult
from app.application.ports import AgentRunRepository, CatalogRepository
from app.application.services.profiles import ProfileService
from app.core.errors import InvalidInputError, UpstreamError
from app.domain.feed import is_qloo_ref
from app.domain.models import Profile
from app.domain.runs import AgentRun, RunKind, RunStatus

logger = logging.getLogger(__name__)

FRIEND_FAVOURITES_MAX = 5
MATCH_TIMEOUT_SECONDS = 45.0
NODE = "match"


class Matcher(Protocol):
    """Compares two tastes (the agent's `compare_tastes` tool, then an insights call)."""

    async def match(self, request: MatchRequest) -> MatchResult:
        """The shared tags, the score and the row. Raises when it can't finish."""
        ...


class TasteMatchService:
    """Taste matches for their owner's profiles only."""

    def __init__(
        self,
        profiles: ProfileService,
        runs: AgentRunRepository,
        catalog: CatalogRepository,
        matcher: Matcher,
    ) -> None:
        self._profiles = profiles
        self._runs = runs
        self._catalog = catalog
        self._matcher = matcher

    async def match(
        self,
        owner_id: UUID,
        profile_id: UUID,
        other_profile_id: UUID | None = None,
        favourites: Sequence[str] | None = None,
    ) -> MatchResult:
        """Match with `other_profile_id` (another of the owner's profiles) or with a friend's
        `favourites` (Qloo entity IDs), not both. Someone else's profile is a 404."""
        profile = await self._profiles.get(owner_id, profile_id)
        other = await self._other(owner_id, profile, other_profile_id, favourites)
        friend_ids = _friend_ids(favourites) if other is None else ()
        run = AgentRun(profile_id=profile.id, kind=RunKind.MATCH)
        await self._runs.add(run)
        request = MatchRequest(profile=profile, run_id=run.id, other=other, friend_ids=friend_ids)
        try:
            result = await asyncio.wait_for(self._matcher.match(request), MATCH_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("Matching tastes failed")
            await RunLog(self._runs, run.id).warn(NODE, "Couldn't compare the tastes.")
            await self._runs.finish(run.id, RunStatus.FAILED, None)
            raise UpstreamError("Couldn't compare tastes just now. Please try again.") from None
        await self._catalog.put_many(list(result.row.items))
        await self._runs.finish(
            run.id,
            RunStatus.DONE,
            {"shared_tags": list(result.shared_tags), "score": result.score},
        )
        return result

    async def _other(
        self,
        owner_id: UUID,
        profile: Profile,
        other_profile_id: UUID | None,
        favourites: Sequence[str] | None,
    ) -> Profile | None:
        if (other_profile_id is None) == (favourites is None):
            raise InvalidInputError("Pick another profile, or add a friend's favourites.")
        if other_profile_id is None:
            return None
        if other_profile_id == profile.id:
            raise InvalidInputError("Pick a different profile to compare with.")
        return await self._profiles.get(owner_id, other_profile_id)


def _friend_ids(favourites: Sequence[str] | None) -> tuple[str, ...]:
    ids = tuple(dict.fromkeys(ref.strip() for ref in favourites or () if ref.strip()))
    if not ids or len(ids) > FRIEND_FAVOURITES_MAX or not all(is_qloo_ref(ref) for ref in ids):
        raise InvalidInputError(f"Add 1 to {FRIEND_FAVOURITES_MAX} favourites found in search.")
    return ids
