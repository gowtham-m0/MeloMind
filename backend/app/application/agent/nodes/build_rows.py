"""Step 4, `build_rows` (code): picks the hero, then builds each registered row in order.

Each row takes research results of its types and runs its own fixed queries within the feed's
Qloo budget. Earlier rows take items first, so an item appears once in the whole feed. Items the
user already loves (their signals) are never recommended back to them.
"""

from collections.abc import Mapping, Sequence

from app.application.agent.deps import FeedDeps
from app.application.agent.ranking import by_popularity, interleave, rank
from app.application.agent.state import FeedState, RowDraft
from app.application.agent.tools.context import ToolContext, ToolRefusalError
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.types import ALL_TYPES, Candidate, FeedContext
from app.application.rows.base import RowSpec

NODE = "build_rows"


async def build_rows(state: FeedState, deps: FeedDeps) -> FeedState:
    """The hero and the row drafts."""
    context = state["context"]
    pool = rank(state.get("pool", []), context.learned_weights, context.previous_refs)
    loved = {signal.ref for signal in context.signals}
    pool = [
        c
        for c in pool
        if c.entity_id not in loved and not context.blocklist.blocks(c.entity_id, c.name)
    ]
    leading = rank(pool, context.learned_weights, context.previous_refs, featured_first=True)
    hero = next((c for c in leading if c.image_url), leading[0] if leading else None)
    used: set[str] = {hero.entity_id} if hero else set()
    if hero:
        await deps.log.info(NODE, f"Top pick: {hero.name}.")
    ctx = ToolContext(
        taste=deps.taste,
        log=deps.log,
        context=context,
        max_qloo_calls=max(deps.limits.feed_max_qloo_calls - state.get("qloo_calls", 0), 0),
        node=NODE,
    )
    ctx.seen.update({candidate.entity_id: candidate for candidate in pool})
    drafts: list[RowDraft] = []
    for row in deps.rows.rows:
        if not row.applies(context):
            continue
        for spec in row.specs(context, pool):
            results = await _run_queries(ctx, spec)
            from_pool = [c for c in pool if c.entity_type in spec.pool_types]
            size = spec.size or deps.limits.row_size
            picks = fill(spec, results + from_pool, used, context, size)
            if len(picks) < spec.min_items:
                await deps.log.info(NODE, f"Left out “{spec.title}”: only {len(picks)} picks.")
                continue
            used.update(candidate.entity_id for candidate in picks)
            drafts.append(
                RowDraft(
                    key=spec.key,
                    title=spec.title,
                    subtitle=spec.subtitle,
                    placement=spec.placement,
                    reason=spec.reason,
                    min_items=spec.min_items,
                    candidates=picks,
                )
            )
            await deps.log.info(NODE, f"{spec.title}: {len(picks)} picks.")
    return {"drafts": drafts, "hero": hero}


async def _run_queries(ctx: ToolContext, spec: RowSpec) -> list[Candidate]:
    """The row's fixed queries. When the budget runs out, the row uses research results only."""
    found: list[Candidate] = []
    for query in spec.queries:
        request = InsightsRequest(
            entity_type=query.entity_type,
            signal_ids=query.signal_ids,
            country_code=query.country_code,
            popularity_min=query.popularity_min,
            year_min=query.year_min,
            year_max=query.year_max,
            take=query.take,
        )
        try:
            found.extend(await get_insights(ctx, request))
        except ToolRefusalError:
            break
    return found


def fill(
    spec: RowSpec,
    candidates: Sequence[Candidate],
    used: set[str],
    context: FeedContext,
    size: int,
) -> list[Candidate]:
    """The row's items: unique, not used by an earlier row, not excluded, not already loved, in
    the row's order."""
    loved = {signal.ref for signal in context.signals}
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        if candidate.entity_id in used or candidate.entity_id in unique:
            continue
        if candidate.entity_id in loved:
            continue
        if context.blocklist.blocks(candidate.entity_id, candidate.name):
            continue
        unique[candidate.entity_id] = candidate
    weights: Mapping[str, float] = context.learned_weights
    ordered = (
        by_popularity(list(unique.values()))
        if spec.order == "popularity"
        else rank(
            list(unique.values()),
            weights,
            context.previous_refs,
            featured_first=spec.order == "featured",
        )
    )
    if spec.one_per_type:
        firsts = {}
        for candidate in ordered:
            firsts.setdefault(candidate.entity_type, candidate)
        ordered = [firsts[t] for t in ALL_TYPES if t in firsts]
    elif spec.mixed:
        ordered = interleave(ordered)
    return ordered[:size]
