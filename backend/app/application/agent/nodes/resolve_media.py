"""Step 5, `resolve_media` (code): find a playable video for each item, swapping an unplayable
one for a spare of the same type. Never an unrelated video. Books need no video.

Spares are resolved only when they may be needed, to save YouTube quota.
"""

import asyncio

from app.application.agent.deps import PlanDeps
from app.application.agent.state import PlanState
from app.application.agent.tools.context import TYPE_NOUNS
from app.application.agent.types import Candidate, PlanContext, PlannedItem
from app.core.errors import UpstreamError
from app.domain.media import media_query
from app.domain.models import EntityType
from app.domain.policies import BOOK_TALK_SECONDS, age_at_release, target_bounds
from app.domain.sessions import MediaRef, SessionItem

NODE = "resolve_media"
MEDIA_CONCURRENCY = 3


def ready(planned: PlannedItem) -> bool:
    """True when the item can be used: it plays, or it's a book (a conversation slot)."""
    return planned.item.entity_type is EntityType.BOOK or planned.item.playable


async def resolve_media(state: PlanState, deps: PlanDeps) -> PlanState:
    """Media for the selected items, then for as many spares as the session may need."""
    context = state["context"]
    ranks = state.get("ranks", {})
    pool = list(state.get("spares", []))
    selected = state.get("selected", [])
    # Look up the selected items a few at a time: each is a separate YouTube call, and too many
    # at once are refused.
    limit = asyncio.Semaphore(MEDIA_CONCURRENCY)

    async def prepare(candidate: Candidate) -> PlannedItem:
        async with limit:
            return await _prepare(deps, context, candidate, ranks)

    prepared_all = await asyncio.gather(*(prepare(candidate) for candidate in selected))
    planned: list[PlannedItem] = []
    for candidate, prepared in zip(selected, prepared_all, strict=True):
        if not ready(prepared):
            swap = await _swap(deps, context, candidate.entity_type, pool, ranks)
            if swap is None:
                await deps.log.info(
                    NODE,
                    f"No playable version of {candidate.name}, and no spare "
                    f"{TYPE_NOUNS[candidate.entity_type]} to swap in.",
                )
            else:
                await deps.log.info(
                    NODE,
                    f"No playable version of {candidate.name}; swapped in {swap.item.title}.",
                )
                prepared = swap
        planned.append(prepared)

    ready_spares: list[PlannedItem] = []
    missing = sum(1 for item in planned if not ready(item))
    low, _ = target_bounds(deps.target_minutes)
    total = sum(item.item.duration_s for item in planned if ready(item))
    for candidate in pool:
        enough_time = not deps.mode.fits_length or total >= low
        if enough_time and len(ready_spares) >= missing:
            break
        prepared = await _prepare(deps, context, candidate, ranks)
        if ready(prepared):
            ready_spares.append(prepared)
            total += prepared.item.duration_s
    videos = [entry for entry in planned if entry.item.entity_type is not EntityType.BOOK]
    playable = sum(1 for entry in videos if entry.item.playable)
    await deps.log.info(NODE, f"Found playable media for {playable} of {len(videos)} items.")
    return {"planned": planned, "ready_spares": ready_spares}


async def _swap(
    deps: PlanDeps,
    context: PlanContext,
    entity_type: EntityType,
    pool: list[Candidate],
    ranks: dict[str, int],
) -> PlannedItem | None:
    for spare in [candidate for candidate in pool if candidate.entity_type is entity_type]:
        pool.remove(spare)
        prepared = await _prepare(deps, context, spare, ranks)
        if ready(prepared):
            return prepared
    return None


async def _prepare(
    deps: PlanDeps, context: PlanContext, candidate: Candidate, ranks: dict[str, int]
) -> PlannedItem:
    item = SessionItem(
        ref=candidate.entity_id,
        title=candidate.name,
        entity_type=candidate.entity_type,
        source=candidate.source,
        reason=candidate.why,
        signal=candidate.signal,
        release_year=candidate.release_year,
        age_at_release=age_at_release(context.birth_year, candidate.release_year),
    )
    rank = ranks.get(candidate.entity_id, len(ranks))
    query = media_query(
        candidate.name, candidate.entity_type, candidate.release_year, context.era_year
    )
    if query is None:
        item.duration_s = BOOK_TALK_SECONDS
        return PlannedItem(item=item, rank=rank)
    try:
        media = await deps.media.resolve(query)
    except UpstreamError:
        await deps.log.warn(NODE, f"The video service didn't answer for {candidate.name}.")
        media = None
    if media is not None:
        item.media = MediaRef(
            provider=media.provider,
            ref=media.video_id,
            duration_s=media.duration_s,
            title=media.title,
        )
        item.duration_s = media.duration_s
    return PlannedItem(item=item, rank=rank)
