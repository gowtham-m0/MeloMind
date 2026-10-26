"""Step 2 of an ask run, `ask_row`: the one extra row, for a mood, a surprise or the user's words.

- A mood searches its tags (`domain/moods.py`), then asks Qloo for each type with those tags and
  the user's strongest signals.
- A surprise looks at the type the user engages with least and takes popular items with lower
  affinity, steered by one signal from another type.
- Words go to the research agent, which turns them into tags and insights calls. If it fails or
  finds too little, the words themselves become a tag search.

The row never repeats what the feed already shows or what the user loves. Everything in it is a
Qloo recommendation (rule 1); the guardrails remove excluded items afterwards (rule 3).
"""

import asyncio
import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from langchain_core.messages import HumanMessage

from app.application.agent.brief import COLD_POPULARITY, PER_TYPE
from app.application.agent.deps import FeedDeps
from app.application.agent.prompts.ask import ask_system_prompt, ask_task
from app.application.agent.ranking import interleave, rank
from app.application.agent.research_agent import (
    RECURSION_LIMIT,
    ModelCallCounter,
    build_research_agent,
)
from app.application.agent.state import FeedState, RowDraft
from app.application.agent.tools.context import TYPE_PLURALS, ToolContext, ToolRefusalError
from app.application.agent.tools.find_tags import find_tags
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.tools.research import research_tools
from app.application.agent.types import ALL_TYPES, AskIntent, Candidate, FeedContext, SignalRef
from app.application.ports import ChatModels, TagMatch
from app.domain.models import EntityType
from app.domain.moods import MOODS

logger = logging.getLogger(__name__)

NODE = "ask"
# An ask row is shown with fewer picks than a feed row, because the user asked for it.
MIN_ITEMS = 3
SURPRISE_POPULARITY = 0.7
SURPRISE_TAKE = 30
SURPRISE_TRIES = 3
FALLBACK_QLOO_CALLS = 8
WORDS_MAX = 3
SIGNALS_PER_QUERY = 2
STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "another",
        "because",
        "been",
        "being",
        "both",
        "could",
        "does",
        "from",
        "have",
        "into",
        "just",
        "like",
        "more",
        "most",
        "much",
        "only",
        "other",
        "really",
        "should",
        "some",
        "something",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "very",
        "want",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
    }
)


async def ask_row(state: FeedState, deps: FeedDeps, intent: AskIntent) -> FeedState:
    """Build the ask row and leave it in `drafts` for the guardrails."""
    context = state["context"]
    ctx = ToolContext(
        taste=deps.taste,
        log=deps.log,
        context=context,
        max_qloo_calls=deps.limits.max_tool_calls,
        node=NODE,
    )
    if intent.surprise:
        title, subtitle, ordered = await _surprise(ctx, deps)
    elif intent.mood:
        title, subtitle, found = await _mood(ctx, intent.mood)
        ordered = _mixed(_fresh(found, context, deps.previous_refs), context, deps)
    else:
        title, subtitle, found = await _words(ctx, deps, intent.text or "")
        ordered = _mixed(_fresh(found, context, deps.previous_refs), context, deps)
    picks = ordered[: deps.limits.row_size]
    if picks:
        await deps.log.info(NODE, f"Built “{title}”: {len(picks)} picks that are new to your feed.")
    else:
        await deps.log.warn(NODE, "Found nothing new for that. Try other words.")
    drafts = [
        RowDraft(
            key="ask",
            title=title,
            subtitle=subtitle,
            placement="main",
            reason=None,
            min_items=MIN_ITEMS,
            candidates=picks,
        )
    ]
    return {"drafts": drafts if picks else [], "single_row": True}


def _fresh(
    candidates: Sequence[Candidate], context: FeedContext, previous_refs: frozenset[str]
) -> list[Candidate]:
    """What is new: not in the feed, not something they love, not excluded, once each."""
    skip = previous_refs | {signal.ref for signal in context.signals}
    seen: set[str] = set()
    kept: list[Candidate] = []
    for candidate in candidates:
        if candidate.entity_id in skip or candidate.entity_id in seen:
            continue
        if context.blocklist.blocks(candidate.entity_id, candidate.name):
            continue
        seen.add(candidate.entity_id)
        kept.append(candidate)
    return kept


def _mixed(
    candidates: Sequence[Candidate], context: FeedContext, deps: FeedDeps
) -> list[Candidate]:
    """Best first, alternating types, so the row moves between music, films, TV and books."""
    ranked = rank(candidates, context.learned_weights, deps.previous_refs, featured_first=True)
    return interleave(ranked)


async def _tags_for(ctx: ToolContext, queries: Sequence[str], what: str) -> list[TagMatch]:
    """The best tag for each query, within the run's Qloo budget."""
    tags: dict[str, TagMatch] = {}
    for query in queries:
        try:
            found = await find_tags(ctx, query)
        except ToolRefusalError:
            if ctx.budget_used:
                break
            continue
        if found:
            tags.setdefault(found[0].tag_id, found[0])
    if tags:
        names = _join([tag.name for tag in tags.values()])
        await ctx.log.info(NODE, f"Turned {what} into the tags {names}.")
    else:
        await ctx.log.warn(NODE, f"Qloo has no tags for {what}, so this follows your taste only.")
    return list(tags.values())


async def _insights_for_types(ctx: ToolContext, tags: Sequence[TagMatch]) -> list[Candidate]:
    """One insights call per type, steered by the tags and the user's strongest signals."""
    signals = tuple(signal.ref for signal in ctx.context.signals if not signal.is_tag)[
        :SIGNALS_PER_QUERY
    ]
    ids = tuple(tag.tag_id for tag in tags) + signals
    found: list[Candidate] = []
    for entity_type in ALL_TYPES:
        request = InsightsRequest(
            entity_type=entity_type,
            signal_ids=ids,
            country_code=ctx.context.country_code,
            popularity_min=None if ids else COLD_POPULARITY,
            take=PER_TYPE,
        )
        try:
            found.extend(await get_insights(ctx, request))
        except ToolRefusalError as refusal:
            if ctx.budget_used:
                break
            await ctx.log.info(NODE, f"Skipped {TYPE_PLURALS[entity_type]}: {refusal.message}")
    return found


async def _mood(ctx: ToolContext, mood_key: str) -> tuple[str, str, list[Candidate]]:
    mood = MOODS[mood_key]
    tags = await _tags_for(ctx, mood.tag_queries, f"a {mood_key} mood")
    found = await _insights_for_types(ctx, tags)
    labelled = [
        replace(candidate, signal=f"fits your {mood_key} mood, {candidate.signal}")
        for candidate in found
    ]
    return f"{mood.label} picks for you", f"Matched to a {mood_key} mood and your taste.", labelled


async def _surprise(ctx: ToolContext, deps: FeedDeps) -> tuple[str, str, list[Candidate]]:
    """Popular picks with lower affinity, from the type the user engages with least. If the
    signal's neighbours are all in the feed already, plain popular picks of that type will do."""
    context = ctx.context
    counts = Counter(signal.entity_type for signal in context.signals if signal.entity_type)
    order = sorted(ALL_TYPES, key=lambda entity_type: counts[entity_type])
    for target in order[:SURPRISE_TRIES]:
        signal = _other_signal(context, target)
        for guide in (signal, None) if signal else (None,):
            picks = await _wildcards(ctx, deps, target, guide)
            if len(picks) >= MIN_ITEMS:
                await ctx.log.info(
                    NODE,
                    f"You engage with {TYPE_PLURALS[target]} least, so the wildcard comes from "
                    "there: popular picks that sit a little outside your usual taste.",
                )
                return (
                    f"Wildcard {TYPE_PLURALS[target]}",
                    "Well-loved picks from outside your usual lane.",
                    picks,
                )
            if ctx.budget_used:
                break
        await ctx.log.info(NODE, f"Too few new {TYPE_PLURALS[target]}; trying another type.")
        if ctx.budget_used:
            break
    return "Wildcard picks", "Well-loved picks from outside your usual lane.", []


async def _wildcards(
    ctx: ToolContext, deps: FeedDeps, target: EntityType, guide: SignalRef | None
) -> list[Candidate]:
    """New popular picks of one type, lower affinity first, with the wildcard reason."""
    request = InsightsRequest(
        entity_type=target,
        signal_ids=(guide.ref,) if guide else (),
        country_code=ctx.context.country_code,
        popularity_min=SURPRISE_POPULARITY,
        take=SURPRISE_TAKE,
    )
    try:
        found = await get_insights(ctx, request)
    except ToolRefusalError as refusal:
        await ctx.log.info(NODE, f"Skipped {TYPE_PLURALS[target]}: {refusal.message}")
        return []
    basis = (
        f"a wildcard: popular with people who like {guide.name}"
        if guide
        else "a wildcard: popular right now"
    )
    wild = [
        replace(
            pick,
            signal=basis,
            because_ref=guide.ref if guide else None,
            because_name=guide.name if guide else None,
        )
        for pick in _fresh(found, ctx.context, deps.previous_refs)
    ]
    # Lower affinity first: liked by people like you, but not the obvious pick.
    wild.sort(key=lambda pick: pick.affinity if pick.affinity is not None else 0.5)
    return wild


def _other_signal(context: FeedContext, target: EntityType) -> SignalRef | None:
    """The strongest signal of another type (never a book for a non-book: Qloo rejects it)."""
    for signal in context.signals:
        if signal.is_tag or signal.entity_type is target:
            continue
        if target is not EntityType.BOOK and signal.entity_type is EntityType.BOOK:
            continue
        return signal
    return None


async def _words(ctx: ToolContext, deps: FeedDeps, text: str) -> tuple[str, str, list[Candidate]]:
    """The agent first; the words as a tag search when it fails or finds too little."""
    found: list[Candidate] = []
    if deps.chat_models is not None:
        found = await _agent_pass(ctx, deps, deps.chat_models, text)
    if len(_fresh(found, ctx.context, deps.previous_refs)) < MIN_ITEMS:
        if deps.chat_models is None:
            await deps.log.info(NODE, "No AI model is set up, so I searched Qloo's tags instead.")
        else:
            await deps.log.warn(NODE, "The agent found too little; searching Qloo's tags instead.")
        fallback = ToolContext(
            taste=deps.taste,
            log=deps.log,
            context=ctx.context,
            max_qloo_calls=FALLBACK_QLOO_CALLS,
            node=NODE,
        )
        tags = await _tags_for(fallback, _queries(text), "your words")
        found = found + await _insights_for_types(fallback, tags)
    return "What you asked for", "Qloo's picks for your request.", found


def _queries(text: str) -> list[str]:
    """The words worth a tag search: longer than 3 letters, not filler, at most three."""
    words = re.findall(r"[^\W\d_][\w'-]*", text.casefold())
    meaningful = [word for word in words if len(word) > 3 and word not in STOP_WORDS]
    return list(dict.fromkeys(meaningful))[:WORDS_MAX]


async def _agent_pass(
    ctx: ToolContext, deps: FeedDeps, models: ChatModels, text: str
) -> list[Candidate]:
    """Run the research agent on the user's words. On any failure, keep what it already found."""
    agent = build_research_agent(
        models,
        research_tools(ctx),
        ask_system_prompt(text, ctx.context, deps.limits.max_tool_calls, ctx.short),
        deps.limits,
        ModelCallCounter(),
    )
    await deps.log.info(NODE, "Asked the AI agent to turn your request into Qloo searches.")
    try:
        await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [HumanMessage(content=ask_task())]},
                config={"recursion_limit": RECURSION_LIMIT},
            ),
            deps.limits.timeout_seconds,
        )
    except TimeoutError:
        await deps.log.warn(NODE, "The agent ran out of time; keeping what it found.")
    except Exception as exc:
        logger.warning("Ask agent failed: %s", type(exc).__name__)
        await deps.log.warn(NODE, "The agent stopped with an error; keeping what it found.")
    if ctx.tag_names:
        await deps.log.info(
            NODE, f"Your request became these tags: {_join(list(ctx.tag_names.values()))}."
        )
    featured = [
        replace(
            candidate,
            signal=candidate.why.rstrip(".") if candidate.why else _matches(candidate),
        )
        for candidate in ctx.submitted.values()
    ]
    others = [
        replace(ctx.seen[ref], signal=_matches(ctx.seen[ref]))
        for ref in ctx.recommended
        if ref in ctx.seen and ref not in ctx.submitted
    ]
    return featured + others


def _join(names: list[str]) -> str:
    """ "A", "A and B" or "A, B and C"."""
    return " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + " and " + names[-1]


def _matches(candidate: Candidate) -> str:
    return f"matches your request, {candidate.signal}"
