"""Taste match: how much two tastes overlap, and a row both may enjoy.

Qloo's compare returns tags, not items. The tags both sides share become the signals of a normal
insights call, so every pick is still a Qloo recommendation (rule 1). With nothing shared, the
row is popular picks and the log says so.
"""

from dataclasses import dataclass, replace

from app.application.agent.brief import COLD_POPULARITY
from app.application.agent.cards import to_card
from app.application.agent.deps import FeedDeps
from app.application.agent.nodes.load_context import load_context
from app.application.agent.ranking import interleave, rank
from app.application.agent.tools.compare_tastes import compare_tastes
from app.application.agent.tools.context import ToolContext, ToolRefusalError
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.types import ALL_TYPES, Candidate, FeedContext
from app.application.ports import TagComparison, TagMatch
from app.domain.feed import FeedRow, is_qloo_ref
from app.domain.feedback import Blocklist
from app.domain.models import EntityType, Profile

NODE = "match"
GROUP_MAX = 5
SHARED_SIGNALS = 5
PER_TYPE = 8
ROW_KEY = "together"
ROW_TITLE = "For you both"
# Popular picks when nothing is shared: artists need a signal, so only these three.
POPULAR_TYPES = (EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK)


@dataclass(frozen=True)
class MatchResult:
    """The tags both tastes share, a 0 to 1 score (a simple heuristic: the share of the smaller
    side's tags that the other side has too) and the "For you both" row."""

    shared_tags: tuple[str, ...]
    score: float
    row: FeedRow


async def match_tastes(
    deps: FeedDeps,
    profile: Profile,
    other: Profile | None,
    friend_ids: tuple[str, ...] = (),
) -> MatchResult:
    """Compare `profile` with another of the owner's profiles, or with a friend's favourites."""
    mine = (await load_context({"profile": profile}, deps))["context"]
    theirs = (await load_context({"profile": other}, deps))["context"] if other else None
    group_a = _group(mine)
    group_b = _group(theirs) if theirs else tuple(ref for ref in friend_ids if is_qloo_ref(ref))
    blocklist = _union(mine.blocklist, theirs.blocklist if theirs else None)
    context = replace(mine, blocklist=blocklist)
    ctx = ToolContext(
        taste=deps.taste,
        log=deps.log,
        context=context,
        max_qloo_calls=deps.limits.max_tool_calls,
        node=NODE,
    )
    comparison = await _compare(ctx, group_a, group_b)
    shared = comparison.shared
    if shared:
        names = ", ".join(tag.name for tag in shared[:SHARED_SIGNALS])
        await deps.log.info(NODE, f"You both like: {names}.")
        found = await _shared_picks(ctx, shared)
    else:
        await deps.log.info(
            NODE, "No shared tags yet, so the row is popular picks you may both enjoy."
        )
        found = await _popular_picks(ctx)
    loved = {signal.ref for signal in mine.signals} | set(group_b)
    if theirs:
        loved |= {signal.ref for signal in theirs.signals}
    fresh = _fresh(found, context, loved)
    ranked = rank(fresh, context.learned_weights, featured_first=False)
    picks = interleave(ranked)[: deps.limits.row_size]
    await deps.log.info(NODE, f"Built “{ROW_TITLE}”: {len(picks)} picks.")
    row = FeedRow(
        key=ROW_KEY,
        title=ROW_TITLE,
        subtitle="Picks that fit both tastes." if shared else "Popular picks for both of you.",
        items=tuple(to_card(pick, context.country_code) for pick in picks),
    )
    return MatchResult(
        shared_tags=tuple(tag.name for tag in shared),
        score=_score(comparison),
        row=row,
    )


def _group(context: FeedContext) -> tuple[str, ...]:
    """Up to five of the strongest Qloo entities of one taste, newest and strongest first."""
    refs = (s.ref for s in context.signals if not s.is_tag and is_qloo_ref(s.ref))
    return tuple(dict.fromkeys(refs))[:GROUP_MAX]


def _union(first: Blocklist, second: Blocklist | None) -> Blocklist:
    """Everything either profile excluded: a row for both is for neither's "no"."""
    if second is None:
        return first
    return Blocklist(refs=first.refs | second.refs, titles=first.titles | second.titles)


async def _compare(
    ctx: ToolContext, group_a: tuple[str, ...], group_b: tuple[str, ...]
) -> TagComparison:
    if not group_a or not group_b:
        await ctx.log.warn(
            NODE, "One side has no Qloo favourites yet, so there is nothing to compare."
        )
        return TagComparison()
    try:
        return await compare_tastes(ctx, group_a, group_b)
    except ToolRefusalError as refusal:
        await ctx.log.warn(NODE, refusal.message)
        return TagComparison()


def _score(comparison: TagComparison) -> float:
    """The shared tags as a share of the smaller side's tags, from 0 to 1."""
    shared = len(comparison.shared)
    if not shared:
        return 0.0
    smaller = min(len(comparison.a_tags), len(comparison.b_tags))
    return round(shared / max(smaller, shared), 2)


async def _shared_picks(ctx: ToolContext, shared: tuple[TagMatch, ...]) -> list[Candidate]:
    tags = shared[:SHARED_SIGNALS]
    ids = tuple(tag.tag_id for tag in tags)
    names = " and ".join(tag.name for tag in tags[:2])
    found: list[Candidate] = []
    for entity_type in ALL_TYPES:
        request = InsightsRequest(
            entity_type=entity_type,
            signal_ids=ids,
            country_code=ctx.context.country_code,
            take=PER_TYPE,
        )
        try:
            found.extend(await get_insights(ctx, request))
        except ToolRefusalError:
            if ctx.budget_used:
                break
    return [replace(pick, signal=f"you both like {names}") for pick in found]


async def _popular_picks(ctx: ToolContext) -> list[Candidate]:
    found: list[Candidate] = []
    for entity_type in POPULAR_TYPES:
        request = InsightsRequest(
            entity_type=entity_type,
            country_code=ctx.context.country_code,
            popularity_min=COLD_POPULARITY,
            take=PER_TYPE,
        )
        try:
            found.extend(await get_insights(ctx, request))
        except ToolRefusalError:
            if ctx.budget_used:
                break
    return found


def _fresh(candidates: list[Candidate], context: FeedContext, loved: set[str]) -> list[Candidate]:
    """Nothing either of them already loves, nothing excluded, once each."""
    seen: set[str] = set()
    kept: list[Candidate] = []
    for candidate in candidates:
        if candidate.entity_id in loved or candidate.entity_id in seen:
            continue
        if context.blocklist.blocks(candidate.entity_id, candidate.name):
            continue
        seen.add(candidate.entity_id)
        kept.append(candidate)
    return kept
