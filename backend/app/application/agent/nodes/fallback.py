"""Step 3, `fallback` (code): runs only when research failed, hit a limit or found too few.

It runs the mode's fixed queries through the same `get_insights` tool, so exclusions still apply,
and relaxes them up to `AGENT_MAX_RETRIES` times for the types that are still short.
"""

from collections.abc import Iterable

from app.application.agent.deps import PlanDeps
from app.application.agent.state import PlanState
from app.application.agent.tools.context import TYPE_PLURALS, ToolContext, ToolRefusalError
from app.application.agent.tools.find_tags import find_tags
from app.application.agent.tools.get_insights import (
    COUNTRY_FILTER_TYPES,
    YEAR_FILTER_TYPES,
    InsightsRequest,
    get_insights,
)
from app.application.agent.types import Candidate, FallbackQuery
from app.application.modes.base import SIGNAL_FROM_TOP
from app.domain.models import EntityType

NODE = "fallback"
TAGS_PER_QUERY = 2
# Enough for every query at every attempt, plus a few tag lookups.
MAX_CALLS = 20

_INTROS = {
    "skipped": "Running the rule-based plan.",
    "too_few": "The agent found too few; running the rule-based plan for the rest.",
    "limit_hit": "Switched to the rule-based plan after the agent's limit.",
    "timeout": "Switched to the rule-based plan after the agent ran out of time.",
    "error": "Switched to the rule-based plan after the agent's error.",
}


async def fallback(state: PlanState, deps: PlanDeps) -> PlanState:
    """Add rule-based candidates to whatever research found."""
    context = state["context"]
    mode = deps.mode
    found: dict[str, Candidate] = {c.entity_id: c for c in state.get("candidates", [])}
    if mode.has_enough(found.values()):
        await deps.log.info(NODE, "The agent's Qloo results are enough; no rule-based queries.")
        return {"candidates": list(found.values()), "fallback_attempts": 0}
    await deps.log.info(
        NODE, _INTROS.get(state.get("research_outcome", "skipped"), _INTROS["skipped"])
    )
    ctx = ToolContext(
        taste=deps.taste, log=deps.log, context=context, max_qloo_calls=MAX_CALLS, node=NODE
    )
    ctx.seen.update(found)
    tags: dict[str, tuple[str, ...]] = {}
    ran: set[tuple[object, ...]] = set()
    base = mode.fallback_queries(context)
    attempts = 0
    for attempt in range(deps.limits.max_retries + 1):
        if attempt and mode.has_enough(found.values()):
            break
        queries = base if attempt == 0 else mode.relax(base, attempt)
        short = mode.shortfall(found.values())
        pending = [query for query in queries if query.entity_type in short] or queries
        if attempt:
            attempts = attempt
            await deps.log.info(NODE, _relax_message(pending[0], attempt))
        for query in pending:
            try:
                await _run(ctx, query, found, tags, ran)
            except ToolRefusalError as refusal:
                await deps.log.warn(NODE, refusal.message)
                break
        if mode.has_enough(found.values()):
            break
    short = mode.shortfall(found.values())
    if short:
        missing = " or ".join(TYPE_PLURALS[entity_type] for entity_type in sorted(short))
        await deps.log.info(NODE, f"Still short of {missing}; other types will fill the gaps.")
    await deps.log.info(NODE, f"The plan now has {len(found)} candidates.")
    return {"candidates": list(found.values()), "fallback_attempts": attempts}


async def _run(
    ctx: ToolContext,
    query: FallbackQuery,
    found: dict[str, Candidate],
    tags: dict[str, tuple[str, ...]],
    ran: set[tuple[object, ...]],
) -> None:
    """Run one query, unless an earlier one already asked Qloo the same thing. (Relaxing the
    era changes nothing for artists, which have no year filter.)"""
    signals = list(query.signal_ids)
    for name in query.tag_queries:
        if name not in tags:
            tags[name] = tuple(tag.tag_id for tag in (await find_tags(ctx, name))[:TAGS_PER_QUERY])
        signals.extend(tags[name])
    if query.signal_from is not None:
        signals.extend(_top_ids(found.values(), query.signal_from))
    if query.entity_type is EntityType.ARTIST and not signals:
        await ctx.log.info(ctx.node, "No era films or tags to guide artist picks; skipped artists.")
        return
    start, end = query.era if query.era else (None, None)
    request = InsightsRequest(
        entity_type=query.entity_type,
        signal_ids=tuple(signals),
        age_55_plus=query.age_55_plus,
        year_min=start,
        year_max=end,
        country_code=query.country_code,
        popularity_min=query.popularity_min,
        take=query.take,
    )
    key = _effective(request)
    if key in ran:
        return
    ran.add(key)
    for candidate in await get_insights(ctx, request):
        found.setdefault(candidate.entity_id, candidate)


def _effective(request: InsightsRequest) -> tuple[object, ...]:
    """What Qloo would actually receive: years and country only where they apply."""
    entity_type = request.entity_type
    years = (request.year_min, request.year_max) if entity_type in YEAR_FILTER_TYPES else None
    country = request.country_code if entity_type in COUNTRY_FILTER_TYPES else None
    return (
        entity_type,
        tuple(sorted(request.signal_ids)),
        request.age_55_plus,
        years,
        country,
        request.popularity_min,
        request.take,
    )


def _top_ids(candidates: Iterable[Candidate], entity_type: EntityType) -> list[str]:
    of_type = [candidate for candidate in candidates if candidate.entity_type is entity_type]
    of_type.sort(key=lambda c: (-(c.affinity or 0.0), -(c.popularity or 0.0)))
    return [candidate.entity_id for candidate in of_type[:SIGNAL_FROM_TOP]]


def _relax_message(query: FallbackQuery, attempt: int) -> str:
    message = "Loosened the search"
    if query.era:
        message += f": widened the era to {query.era[0]}–{query.era[1]}"
    if attempt >= 2 and query.popularity_min is not None:
        message += f" and lowered the popularity floor to {query.popularity_min}"
    return message + "."
