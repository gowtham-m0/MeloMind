"""Tests for the agent's tools: validation, exclusions, budgets and logging."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from app.application.agent.tools.context import NO_CALLS_LEFT, ToolContext, ToolRefusalError
from app.application.agent.tools.find_tags import find_tags
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.tools.research import research_tools
from app.application.agent.tools.search_entities import search_entities
from app.application.agent.tools.submit_candidates import submit_candidates
from app.domain.feedback import Exclusion, ExclusionKind
from app.domain.models import EntityType
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import (
    MARGARET_FAVOURITES,
    SOUND_OF_MUSIC,
    SUPREMES,
    FailingTasteGraph,
    RecordingTasteGraph,
    log_messages,
    make_context,
    make_log,
)

pytestmark = pytest.mark.anyio

FOUR_TOPS = "demo-artist-the-four-tops"


async def make_ctx(
    graph: object | None = None, max_calls: int = 12, **context: object
) -> tuple[ToolContext, RecordingTasteGraph]:
    recorder = RecordingTasteGraph(graph or FixtureTasteGraph())
    log, _ = await make_log()
    ctx = ToolContext(
        taste=recorder,
        log=log,
        context=make_context(favourites=MARGARET_FAVOURITES, **context),  # type: ignore[arg-type]
        max_qloo_calls=max_calls,
    )
    return ctx, recorder


async def test_get_insights_always_adds_the_profiles_exclusions() -> None:
    blocked = [Exclusion(uuid4(), FOUR_TOPS, "The Four Tops", ExclusionKind.REJECTED)]
    ctx, recorder = await make_ctx(blocked=blocked)

    found = await get_insights(
        ctx, InsightsRequest(EntityType.ARTIST, signal_ids=(SUPREMES.ref,), take=20)
    )

    assert recorder.insights_queries[0].exclude_entities == (FOUR_TOPS,)
    assert FOUR_TOPS not in {candidate.entity_id for candidate in found}
    assert found


async def test_get_insights_drops_years_for_artists_and_country_for_books() -> None:
    ctx, recorder = await make_ctx()

    await get_insights(
        ctx,
        InsightsRequest(
            EntityType.ARTIST, (SUPREMES.ref,), year_min=1961, year_max=1969, country_code="US"
        ),
    )
    await get_insights(
        ctx,
        InsightsRequest(
            EntityType.BOOK, (SUPREMES.ref,), year_min=1969, year_max=1961, country_code="US"
        ),
    )

    artist, book = recorder.insights_queries
    assert (artist.year_min, artist.year_max, artist.country_code) == (None, None, None)
    assert (book.year_min, book.year_max, book.country_code) == (1961, 1969, None)


async def test_get_insights_ignores_unknown_ids_and_clamps_take() -> None:
    ctx, recorder = await make_ctx()

    await get_insights(
        ctx, InsightsRequest(EntityType.MOVIE, ("made-up-id", SOUND_OF_MUSIC.ref), take=99)
    )

    query = recorder.insights_queries[0]
    assert query.signal_entities == (SOUND_OF_MUSIC.ref,)
    assert query.take == 20


async def test_artists_are_never_asked_for_with_the_age_signal_alone() -> None:
    ctx, recorder = await make_ctx()

    with pytest.raises(ToolRefusalError):
        await get_insights(ctx, InsightsRequest(EntityType.ARTIST, age_55_plus=True))

    assert recorder.insights_queries == []


async def test_a_qloo_failure_is_logged_and_gives_no_candidates() -> None:
    ctx, _ = await make_ctx(FailingTasteGraph())

    found = await get_insights(ctx, InsightsRequest(EntityType.MOVIE, (SOUND_OF_MUSIC.ref,)))

    assert found == []
    assert "didn't answer" in (await log_messages(ctx.log._runs, ctx.log))[-1]  # type: ignore[arg-type]


async def test_search_refuses_song_titles() -> None:
    ctx, recorder = await make_ctx(song_titles=("My Girl",))

    with pytest.raises(ToolRefusalError, match="Qloo has no songs"):
        await search_entities(ctx, "my girl")

    assert recorder.searches == []


async def test_an_empty_search_is_logged_so_the_agent_can_try_the_next_hint() -> None:
    ctx, _ = await make_ctx(RecordingTasteGraph(FixtureTasteGraph(), empty_searches=["TMS"]))

    first = await search_entities(ctx, "TMS", EntityType.ARTIST)
    second = await search_entities(ctx, "T. M. Soundararajan", EntityType.ARTIST)

    messages = await log_messages(ctx.log._runs, ctx.log)  # type: ignore[arg-type]
    assert first == []
    assert second
    assert messages == [
        "Searched artist TMS → no match ✗.",
        "Searched artist T. M. Soundararajan → 1 found ✓.",
    ]


async def test_the_qloo_call_budget_is_enforced_by_the_tools() -> None:
    ctx, recorder = await make_ctx(max_calls=2)

    await find_tags(ctx, "Tamil")
    await search_entities(ctx, "The Beatles")
    with pytest.raises(ToolRefusalError, match=NO_CALLS_LEFT):
        await get_insights(ctx, InsightsRequest(EntityType.MOVIE, (SOUND_OF_MUSIC.ref,)))

    assert recorder.insights_queries == []
    assert ctx.budget_used


async def test_submit_accepts_only_qloo_recommendations_that_are_not_blocked() -> None:
    blocked = [Exclusion(uuid4(), "demo-artist-marvin-gaye", "Marvin Gaye", ExclusionKind.HIDDEN)]
    ctx, _ = await make_ctx(blocked=blocked)
    recommended = await get_insights(ctx, InsightsRequest(EntityType.ARTIST, (SUPREMES.ref,)))
    await search_entities(ctx, "The Beatles")
    ctx.recommended.add("demo-artist-marvin-gaye")
    ctx.seen["demo-artist-marvin-gaye"] = replace(
        recommended[0], entity_id="demo-artist-marvin-gaye", name="Marvin Gaye"
    )

    result = await submit_candidates(
        ctx,
        [
            (recommended[0].entity_id, "Motown, like The Supremes"),
            ("demo-artist-the-beatles", "Searched by name only"),
            ("invented-id", "Sounds nice"),
            ("demo-artist-marvin-gaye", "Motown"),
        ],
    )

    assert result.accepted == 1
    assert result.unknown_ids == ("demo-artist-the-beatles", "invented-id")
    assert result.blocked == 1
    assert list(ctx.submitted) == [recommended[0].entity_id]
    assert ctx.submitted[recommended[0].entity_id].why == "Motown, like The Supremes"


async def test_the_langchain_tools_return_json_and_refusals_as_text() -> None:
    ctx, _ = await make_ctx(song_titles=("My Girl",))
    tools = {tool.name: tool for tool in research_tools(ctx)}

    refused = await tools["search_entities"].ainvoke({"name": "My Girl"})
    found = json.loads(await tools["search_entities"].ainvoke({"name": "The Beatles"}))
    insights = json.loads(
        await tools["get_insights"].ainvoke(
            {"type": "movie", "signal_ids": [SOUND_OF_MUSIC.ref, "nope"], "take": 3}
        )
    )
    picks = [
        {"entity_id": insights["candidates"][0]["entity_id"], "why": "A 60s musical"},
        {"entity_id": found[0]["entity_id"], "why": "Only searched for"},
    ]
    submitted = json.loads(await tools["submit_candidates"].ainvoke({"candidates": picks}))

    assert "Qloo has no songs" in refused
    assert found[0]["name"] == "The Beatles"
    assert len(insights["candidates"]) == 3
    assert set(insights["candidates"][0]) == {"entity_id", "name", "year", "affinity"}
    assert insights["ignored_unknown_ids"] == ["nope"]
    assert submitted["accepted"] == 1
    assert submitted["refused_unknown_ids"] == [found[0]["entity_id"]]
    assert tools["submit_candidates"].return_direct
