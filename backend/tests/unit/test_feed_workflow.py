"""Tests for the build_feed workflow, with a scripted chat model and the demo fixtures."""

from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.application.agent.builder import AgentFeedBuilder, FeedRequest, FeedResult
from app.application.agent.deps import AgentLimits
from app.application.agent.prompts.explain import ExplainOutput
from app.application.ports import ChatModels, LanguageModel
from app.application.rows.registry import default_registry
from app.domain.feed import FeedItem
from app.domain.feedback import Exclusion, Feedback, Signal
from app.domain.models import EntityType, Favourite, FavouriteKind, Profile
from app.domain.runs import AgentRun, RunKind
from app.infrastructure.persistence.memory_feedback import (
    InMemoryExclusionRepository,
    InMemoryFeedbackRepository,
)
from app.infrastructure.persistence.memory_runs import InMemoryAgentRunRepository
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import FakeLanguageModel, ScriptedChatModel, tool_call, turn

pytestmark = pytest.mark.anyio

SUPREMES = "demo-artist-the-supremes"
SOUND_OF_MUSIC = "demo-movie-the-sound-of-music"
MOCKINGBIRD = "demo-book-to-kill-a-mockingbird"
FEATURED = [
    "demo-artist-the-four-tops",
    "demo-movie-mary-poppins",
    "demo-tv-shindig",
    "demo-book-catch-22",
]


def leo(birth_year: int | None = 1950) -> Profile:
    profile = Profile(
        owner_id=uuid4(), display_name="Leo", birth_year=birth_year, country_code="US"
    )
    for name, kind, qloo_id in [
        ("The Supremes", FavouriteKind.ARTIST, SUPREMES),
        ("The Sound of Music", FavouriteKind.MOVIE, SOUND_OF_MUSIC),
        ("To Kill a Mockingbird", FavouriteKind.BOOK, MOCKINGBIRD),
    ]:
        profile.favourites.append(Favourite(profile.id, name, kind, qloo_id=qloo_id))
    return profile


def research_script() -> list[Any]:
    return [
        turn(
            tool_call("get_insights", "1", type="artist", signal_ids=[SUPREMES]),
            tool_call("get_insights", "2", type="movie", signal_ids=[SOUND_OF_MUSIC]),
            tool_call("get_insights", "3", type="tv_show", signal_ids=[SUPREMES]),
            tool_call("get_insights", "4", type="book", signal_ids=[MOCKINGBIRD]),
        ),
        turn(
            tool_call(
                "submit_candidates",
                "5",
                candidates=[{"entity_id": ref, "why": "A classic"} for ref in FEATURED],
            )
        ),
    ]


async def build(
    profile: Profile,
    *,
    chat: ScriptedChatModel | None = None,
    language_model: LanguageModel | None = None,
    limits: AgentLimits | None = None,
    excluded: list[str] | None = None,
    feedback: list[Feedback] | None = None,
    previous_refs: frozenset[str] = frozenset(),
) -> tuple[FeedResult, list[str]]:
    runs = InMemoryAgentRunRepository()
    exclusions = InMemoryExclusionRepository()
    for ref in excluded or []:
        await exclusions.save(Exclusion(profile.id, ref, ref))
    signals = InMemoryFeedbackRepository()
    for entry in feedback or []:
        await signals.add(entry)
    run = AgentRun(profile_id=profile.id, kind=RunKind.FEED)
    await runs.add(run)
    builder = AgentFeedBuilder(
        feedback=signals,
        exclusions=exclusions,
        taste=FixtureTasteGraph(),
        runs=runs,
        rows=default_registry(),
        limits=limits or AgentLimits(),
        language_model=language_model,
        chat_models=ChatModels(primary=chat) if chat else None,
    )
    result = await builder.build(FeedRequest(profile, run.id, previous_refs=previous_refs))
    stored = await runs.get(run.id)
    assert stored is not None
    return result, [f"{step.node}: {step.message}" for step in stored.steps]


def every_item(result: FeedResult) -> list[FeedItem]:
    return ([result.hero] if result.hero else []) + [i for row in result.rows for i in row.items]


async def test_the_agent_researches_and_its_featured_picks_lead_the_feed() -> None:
    chat = ScriptedChatModel(script=research_script())

    result, log = await build(leo(), chat=chat)

    # The 1960s fixtures have few TV shows, so the fallback may top that type up.
    assert result.run_summary["research_outcome"] in ("ok", "too_few")
    assert chat.calls == 2
    first_row = result.rows[0]
    assert first_row.key == "for_you"
    leading = [result.hero.ref] if result.hero else []
    leading += [item.ref for item in first_row.items[:4]]
    assert set(FEATURED) <= set(leading)
    assert "research: Submitted 4 candidates." in log


async def test_without_a_model_the_rule_based_fallback_still_builds_a_feed() -> None:
    result, log = await build(leo())

    assert result.run_summary["research_outcome"] == "skipped"
    assert len(result.rows) >= 4
    assert any("rule-based" in line for line in log)
    assert {item.entity_type for item in every_item(result)} == set(EntityType)


async def test_the_research_agent_stops_at_its_limit_and_the_fallback_fills_in() -> None:
    looping = [
        turn(tool_call("get_insights", str(i), type="artist", signal_ids=[SUPREMES]))
        for i in range(10)
    ]
    chat = ScriptedChatModel(script=looping)

    result, log = await build(leo(), chat=chat, limits=AgentLimits(max_tool_calls=2))

    assert result.run_summary["research_outcome"] == "limit_hit"
    assert any(line.startswith("fallback:") for line in log)
    assert len(result.rows) >= 3


async def test_an_item_appears_at_most_once_and_every_item_has_a_source_and_reason() -> None:
    result, _ = await build(leo(), chat=ScriptedChatModel(script=research_script()))

    refs = [item.ref for item in every_item(result)]
    assert len(refs) == len(set(refs))
    for item in every_item(result):
        assert item.source
        assert item.reason.strip()
        assert item.links


async def test_excluded_items_never_appear_anywhere() -> None:
    first, _ = await build(leo())
    excluded = [item.ref for item in every_item(first)[:5]]

    second, _ = await build(leo(), excluded=excluded)

    assert not set(excluded) & {item.ref for item in every_item(second)}


async def test_the_users_own_favourites_are_never_recommended_back() -> None:
    result, _ = await build(leo())

    refs = {item.ref for item in every_item(result)}
    assert not refs & {SUPREMES, SOUND_OF_MUSIC, MOCKINGBIRD}


async def test_likes_become_signals_and_get_their_own_row() -> None:
    profile = leo()
    liked = Feedback(
        profile.id,
        "demo-artist-the-temptations",
        "The Temptations",
        Signal.LIKED,
        EntityType.ARTIST,
    )

    result, log = await build(profile, feedback=[liked])

    assert "Because you liked The Temptations" in [row.title for row in result.rows]
    assert any("Steering by The Temptations (you liked it)." in line for line in log)


async def test_cross_culture_picks_cross_types_and_skip_book_signals() -> None:
    result, _ = await build(leo())

    rail = next(row for row in result.rows if row.placement == "rail")
    assert rail.subtitle == "Because you like The Supremes…"
    assert len({item.entity_type for item in rail.items}) == len(rail.items)


async def test_throwback_needs_a_birth_year() -> None:
    with_year, _ = await build(leo(1950))
    without, _ = await build(leo(None))

    assert not any(row.key == "throwback" for row in without.rows)
    assert all(row.key != "throwback" or row.items for row in with_year.rows)


async def test_the_summary_uses_the_llm_after_the_first_feed() -> None:
    def answer(schema: type[BaseModel], prompt: str) -> BaseModel:
        return ExplainOutput(summary="More Motown today.")

    first, _ = await build(leo(), language_model=FakeLanguageModel(answer))
    again, _ = await build(
        leo(),
        language_model=FakeLanguageModel(answer),
        previous_refs=frozenset(item.ref for item in every_item(first)),
    )

    assert first.summary.startswith("Your feed is ready")
    assert again.summary == "More Motown today."


async def test_an_llm_failure_falls_back_to_the_template_summary() -> None:
    result, log = await build(
        leo(), language_model=FakeLanguageModel(None), previous_refs=frozenset({"old"})
    )

    assert result.summary
    assert "explain: The AI summary didn't come back; used a template." in log
