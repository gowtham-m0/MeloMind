"""Step 3, `fallback` (code): runs only when research failed, hit a limit or left a type short.

It runs fixed queries through the same `get_insights` tool, so exclusions still apply, and
relaxes them up to `AGENT_MAX_RETRIES` times for the types that are still short: first it drops
the popularity floor, then it adds the next few signals.
"""

from collections.abc import Iterable

from app.application.agent.brief import COLD_POPULARITY, PER_TYPE, has_enough, shortfall
from app.application.agent.deps import FeedDeps
from app.application.agent.state import FeedState
from app.application.agent.tools.context import TYPE_PLURALS, ToolContext, ToolRefusalError
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.types import ALL_TYPES, Candidate, FallbackQuery, FeedContext
from app.domain.models import EntityType

NODE = "fallback"
SIGNALS_PER_QUERY = 3
SIGNAL_FROM_TOP = 3
TAKE = PER_TYPE + 6
# Enough for every type at every attempt.
MAX_CALLS = 12
# Films first, so cold-start artists can follow the popular films.
QUERY_ORDER = (EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK, EntityType.ARTIST)

_INTROS = {
    "skipped": "Finding picks with the rule-based queries.",
    "too_few": "Some types came back thin; topping them up with rule-based queries.",
    "limit_hit": "Switched to rule-based queries after the agent's limit.",
    "timeout": "Switched to rule-based queries after the agent ran out of time.",
    "error": "Switched to rule-based queries after the agent's error.",
}


def fallback_queries(context: FeedContext, attempt: int) -> list[FallbackQuery]:
    """One query per type. Signals rotate with each attempt; with no signals, popular picks for
    the country, and artists follow those films."""
    signals = [signal.ref for signal in context.signals]
    start = attempt * SIGNALS_PER_QUERY
    chosen = tuple(signals[start : start + SIGNALS_PER_QUERY]) or tuple(signals[:SIGNALS_PER_QUERY])
    queries: list[FallbackQuery] = []
    for entity_type in QUERY_ORDER:
        if chosen:
            query = FallbackQuery(entity_type=entity_type, take=TAKE, signal_ids=chosen)
        elif entity_type is EntityType.ARTIST:
            query = FallbackQuery(entity_type=entity_type, take=TAKE, signal_from=EntityType.MOVIE)
        else:
            query = FallbackQuery(
                entity_type=entity_type,
                take=TAKE,
                country_code=context.country_code,
                popularity_min=COLD_POPULARITY if attempt == 0 else None,
            )
        queries.append(query)
    return queries


async def fallback(state: FeedState, deps: FeedDeps) -> FeedState:
    """Add rule-based candidates to whatever research found."""
    context = state["context"]
    found: dict[str, Candidate] = {c.entity_id: c for c in state.get("pool", [])}
    if has_enough(found.values()):
        await deps.log.info(NODE, "The agent's Qloo results are enough; no rule-based queries.")
        return {"pool": list(found.values()), "fallback_attempts": 0}
    await deps.log.info(
        NODE, _INTROS.get(state.get("research_outcome", "skipped"), _INTROS["skipped"])
    )
    ctx = ToolContext(
        taste=deps.taste, log=deps.log, context=context, max_qloo_calls=MAX_CALLS, node=NODE
    )
    ctx.seen.update(found)
    attempts = 0
    for attempt in range(deps.limits.max_retries + 1):
        short = shortfall(found.values())
        if not short:
            break
        if attempt:
            attempts = attempt
            await deps.log.info(NODE, "Loosened the search for the types still short.")
        pending = [
            query for query in fallback_queries(context, attempt) if query.entity_type in short
        ]
        try:
            for query in pending:
                await _run(ctx, query, found)
        except ToolRefusalError as refusal:
            await deps.log.warn(NODE, refusal.message)
            break
    short = shortfall(found.values())
    if short:
        missing = " or ".join(
            TYPE_PLURALS[entity_type] for entity_type in ALL_TYPES if entity_type in short
        )
        await deps.log.info(NODE, f"Still short of {missing}; those rows may be smaller.")
    await deps.log.info(NODE, f"The pool now has {len(found)} picks.")
    return {
        "pool": list(found.values()),
        "fallback_attempts": attempts,
        "qloo_calls": state.get("qloo_calls", 0) + ctx.qloo_calls,
    }


async def _run(ctx: ToolContext, query: FallbackQuery, found: dict[str, Candidate]) -> None:
    signals = list(query.signal_ids)
    if query.signal_from is not None:
        signals.extend(_top_ids(found.values(), query.signal_from))
        if not signals:
            await ctx.log.info(ctx.node, "No films yet to guide artist picks; skipped artists.")
            return
    request = InsightsRequest(
        entity_type=query.entity_type,
        signal_ids=tuple(signals),
        country_code=query.country_code,
        popularity_min=query.popularity_min,
        take=query.take,
    )
    for candidate in await get_insights(ctx, request):
        found.setdefault(candidate.entity_id, candidate)


def _top_ids(candidates: Iterable[Candidate], entity_type: EntityType) -> list[str]:
    of_type = [candidate for candidate in candidates if candidate.entity_type is entity_type]
    of_type.sort(key=lambda c: (-(c.affinity or 0.0), -(c.popularity or 0.0)))
    return [candidate.entity_id for candidate in of_type[:SIGNAL_FROM_TOP]]
