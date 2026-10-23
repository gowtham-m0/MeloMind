"""Tests for the plan_session workflow, with a scripted chat model and fake media. No network."""

import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.application.agent.deps import AgentLimits
from app.application.agent.planner import AgentPlanner, PlanRequest, PlanResult
from app.application.agent.prompts.compose import ComposedItem
from app.application.modes.registry import default_registry
from app.application.ports import ChatModels, LanguageModel
from app.domain.feedback import Exclusion, ExclusionKind
from app.domain.models import Favourite, FavouriteKind, Profile
from app.domain.policies import target_bounds
from app.domain.runs import AgentRun, RunKind
from app.infrastructure.media.demo import DemoMediaResolver
from app.infrastructure.persistence.memory_feedback import (
    InMemoryExclusionRepository,
    InMemoryFeedbackRepository,
)
from app.infrastructure.persistence.memory_runs import InMemoryAgentRunRepository
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import FakeLanguageModel, ScriptedChatModel, tool_call, turn

pytestmark = pytest.mark.anyio

ERA = {"year_min": 1961, "year_max": 1969}
PICKS = [
    "demo-artist-the-four-tops",
    "demo-artist-marvin-gaye",
    "demo-artist-stevie-wonder",
    "demo-artist-aretha-franklin",
    "demo-artist-martha-and-the-vandellas",
    "demo-movie-mary-poppins",
    "demo-movie-my-fair-lady",
    "demo-movie-west-side-story",
    "demo-tv-shindig",
    "demo-book-catch-22",
    "demo-book-the-bell-jar",
]


def margaret() -> Profile:
    profile = Profile(owner_id=uuid4(), display_name="Margaret", birth_year=1948, country_code="US")
    for name, kind, qloo_id in [
        ("The Supremes", FavouriteKind.ARTIST, "demo-artist-the-supremes"),
        ("The Sound of Music", FavouriteKind.MOVIE, "demo-movie-the-sound-of-music"),
        ("To Kill a Mockingbird", FavouriteKind.BOOK, "demo-book-to-kill-a-mockingbird"),
    ]:
        profile.favourites.append(Favourite(profile.id, name, kind, qloo_id=qloo_id))
    return profile


def research_script() -> list[Any]:
    return [
        turn(
            tool_call("get_insights", "1", type="artist", signal_ids=["demo-artist-the-supremes"]),
            tool_call(
                "get_insights",
                "2",
                type="movie",
                signal_ids=["demo-movie-the-sound-of-music"],
                **ERA,
            ),
            tool_call(
                "get_insights", "3", type="tv_show", signal_ids=["demo-artist-the-supremes"], **ERA
            ),
            tool_call(
                "get_insights",
                "4",
                type="book",
                signal_ids=["demo-book-to-kill-a-mockingbird"],
                **ERA,
            ),
        ),
        turn(
            tool_call(
                "submit_candidates",
                "5",
                candidates=[{"entity_id": ref, "why": "Fits her era."} for ref in PICKS],
            )
        ),
    ]


async def plan(
    profile: Profile,
    *,
    chat: ScriptedChatModel | None = None,
    language_model: LanguageModel | None = None,
    limits: AgentLimits | None = None,
    blocked: list[str] | None = None,
) -> tuple[PlanResult, list[str]]:
    runs = InMemoryAgentRunRepository()
    exclusions = InMemoryExclusionRepository()
    for ref in blocked or []:
        await exclusions.save(Exclusion(profile.id, ref, ref, ExclusionKind.REJECTED))
    run = AgentRun(profile_id=profile.id, kind=RunKind.PLAN)
    await runs.add(run)
    planner = AgentPlanner(
        feedback=InMemoryFeedbackRepository(),
        exclusions=exclusions,
        taste=FixtureTasteGraph(),
        media=DemoMediaResolver(),
        runs=runs,
        limits=limits or AgentLimits(),
        language_model=language_model,
        chat_models=ChatModels(primary=chat) if chat else None,
    )
    mode = default_registry().get("standard")
    result = await planner.plan(PlanRequest(profile, mode, 20, run.id))
    stored = await runs.get(run.id)
    assert stored is not None
    return result, [f"{step.node}: {step.message}" for step in stored.steps]


async def test_the_agent_researches_and_the_fallback_is_skipped() -> None:
    result, log = await plan(margaret(), chat=ScriptedChatModel(script=research_script()))

    assert result.summary["research_outcome"] == "ok"
    assert not any(line.startswith("fallback") for line in log)
    assert any(line.startswith("research: Asked Qloo for films") for line in log)
    assert {item.ref for item in result.items} <= set(PICKS)
    assert all(item.source and item.signal for item in result.items)


async def test_hitting_the_call_limit_hands_over_to_the_fallback() -> None:
    result, log = await plan(
        margaret(),
        chat=ScriptedChatModel(script=research_script()[:1]),
        limits=AgentLimits(max_tool_calls=2),
    )

    assert result.summary["research_outcome"] == "limit_hit"
    assert "research: Used all 2 Qloo calls." in log
    assert any(line.startswith("fallback: Switched to the rule-based plan") for line in log)
    assert result.items


async def test_a_failing_model_still_produces_a_session_within_length() -> None:
    result, _ = await plan(margaret(), chat=ScriptedChatModel(script=[], fail_first=99))

    low, high = target_bounds(20)
    assert result.summary["research_outcome"] in {"error", "timeout"}
    assert low <= result.summary["total_duration_s"] <= high


async def test_excluded_items_never_return() -> None:
    blocked = ["demo-artist-the-four-tops", "demo-movie-mary-poppins"]
    result, log = await plan(
        margaret(), chat=ScriptedChatModel(script=research_script()), blocked=blocked
    )

    assert not {item.ref for item in result.items} & set(blocked)
    # Qloo never returned them (the tool excluded them), so the agent's picks were refused.
    assert any("Refused 2 that Qloo didn't recommend" in line for line in log)


async def test_an_llm_failure_in_compose_falls_back_to_templates() -> None:
    result, log = await plan(margaret(), language_model=FakeLanguageModel(answer=None))

    assert "compose: The AI didn't answer in time; used templates." in log
    assert all(item.reason and item.prompt for item in result.items)
    assert not any("remember" in (item.prompt or "").lower() for item in result.items)


async def test_a_birth_year_alone_still_plans_a_session() -> None:
    profile = Profile(owner_id=uuid4(), display_name="Bob", birth_year=1948)

    result, _ = await plan(profile)

    assert len(result.items) >= 4


def llm_answer(schema: type[BaseModel], prompt: str) -> BaseModel:
    refs = [row["ref"] for row in json.loads(prompt)["items"]]
    composed = [
        ComposedItem(ref=ref, reason="Picked for Margaret.", prompt="What do you love about it?")
        for ref in refs
    ]
    composed[0] = ComposedItem(ref=refs[0], reason="Fine.", prompt="Do you remember this song?")
    composed[1] = ComposedItem(ref=refs[1], reason="Music therapy helps.", prompt="Hum along?")
    return schema.model_validate({"items": [item.model_dump() for item in composed[:-1]]})


async def test_compose_uses_the_llm_but_code_replaces_unsafe_or_missing_lines() -> None:
    result, log = await plan(margaret(), language_model=FakeLanguageModel(answer=llm_answer))

    first, second, *_, last = result.items
    assert first.reason == "Fine."
    assert first.prompt is not None and "remember" not in first.prompt.lower()
    assert "therapy" not in second.reason.lower()
    assert result.items[2].reason == "Picked for Margaret."
    assert last.reason and last.prompt
    assert "compose: Used templates for 1 item(s) the AI left out." in log
    assert "compose: Replaced 2 line(s) that tested memory or sounded medical." in log


async def test_a_slow_agent_is_stopped_and_the_fallback_still_plans() -> None:
    slow = ScriptedChatModel(script=research_script(), delay_s=2)

    result, log = await plan(margaret(), chat=slow, limits=AgentLimits(timeout_seconds=1))

    assert result.summary["research_outcome"] == "timeout"
    assert any("ran out of time" in line for line in log)
    assert result.items


async def test_a_timed_out_agent_keeps_the_qloo_recommendations_it_found() -> None:
    slow_after_tools = ScriptedChatModel(script=research_script(), delay_s=2, delay_from=1)

    result, log = await plan(
        margaret(), chat=slow_after_tools, limits=AgentLimits(timeout_seconds=1)
    )

    assert result.summary["research_outcome"] == "timeout"
    assert any("recommendations Qloo had given it" in line for line in log)
    assert "fallback: The agent's Qloo results are enough; no rule-based queries." in log
    assert not any(line.startswith("fallback: Asked Qloo") for line in log)
    assert result.items
