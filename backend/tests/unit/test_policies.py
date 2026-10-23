"""Tests for the learning rules in domain/policies.py."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.feedback import Actor, Feedback, PersonSignal
from app.domain.policies import (
    age_at_release,
    counted_today,
    era_window,
    is_memory_test,
    learned_weights,
    makes_medical_claim,
    rank_key,
    signal_refs,
    skip_counts,
    target_bounds,
)

PROFILE = uuid4()
MORNING = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)


def entry(ref: str, actor: Actor, kind: str, at: datetime = MORNING) -> Feedback:
    return Feedback(
        profile_id=PROFILE, item_ref=ref, title=ref, actor=actor, kind=kind, created_at=at
    )


def test_era_window_is_13_to_21_and_widens_by_5_per_retry() -> None:
    assert era_window(1948) == (1961, 1969)
    assert era_window(1948, 1) == (1956, 1974)
    assert era_window(1948, 2) == (1951, 1979)


@pytest.mark.parametrize(
    ("kind", "weight"),
    [("sang_along", 1.0), ("smiled", 0.6), ("calm", 0.2), ("neutral", 0.0), ("upset", 0.0)],
)
def test_caregiver_weights(kind: str, weight: float) -> None:
    assert learned_weights([entry("a", Actor.CAREGIVER, kind)]).get("a", 0.0) == weight


@pytest.mark.parametrize(
    ("kind", "weight"), [("chose", 0.3), ("loved", 0.6), ("replayed", 0.6), ("skipped", -0.2)]
)
def test_person_weights(kind: str, weight: float) -> None:
    assert learned_weights([entry("a", Actor.PERSON, kind)]) == {"a": weight}


def test_each_person_signal_counts_once_per_item_per_day() -> None:
    taps = [entry("a", Actor.PERSON, "loved", MORNING + timedelta(minutes=m)) for m in range(5)]
    taps.append(entry("a", Actor.PERSON, "loved", MORNING + timedelta(days=1)))

    assert learned_weights(taps) == {"a": 1.2}
    assert counted_today(taps, "a", PersonSignal.LOVED, MORNING)
    assert not counted_today(taps, "a", PersonSignal.REPLAYED, MORNING)


def test_caregiver_reactions_are_never_deduplicated() -> None:
    reactions = [entry("a", Actor.CAREGIVER, "smiled"), entry("a", Actor.CAREGIVER, "smiled")]

    assert learned_weights(reactions) == {"a": 1.2}


def test_items_at_or_above_point_six_become_signals_highest_first() -> None:
    weights = {"low": 0.3, "edge": 0.6, "high": 1.6, "negative": -0.2}

    assert signal_refs(weights) == ["high", "edge"]


@pytest.mark.parametrize(
    ("played_s", "counts"), [(0, True), (14, True), (15, False), (None, False)]
)
def test_a_skip_counts_only_under_15_seconds(played_s: int | None, counts: bool) -> None:
    assert skip_counts(played_s) is counts


def test_ranking_is_affinity_then_learned_weight_then_popularity() -> None:
    items = {
        "strong": rank_key(0.95, 0.0, 0.1),
        "liked": rank_key(0.82, 1.0, 0.1),
        "popular": rank_key(0.84, 0.0, 0.99),
        "plain": rank_key(0.83, 0.0, 0.5),
    }

    assert sorted(items, key=items.__getitem__) == ["strong", "liked", "popular", "plain"]


def test_age_at_release() -> None:
    assert age_at_release(1948, 1965) == 17
    assert age_at_release(1948, None) is None
    assert age_at_release(1948, 1940) is None


def test_target_bounds_are_ten_percent_either_side() -> None:
    assert target_bounds(20) == (1080, 1320)


@pytest.mark.parametrize(
    "prompt", ["Do you remember this song?", "Can you recall who sang it?", "You'd remember this"]
)
def test_memory_tests_are_caught(prompt: str) -> None:
    assert is_memory_test(prompt)


def test_open_prompts_pass() -> None:
    assert not is_memory_test("What does this song bring to mind?")


@pytest.mark.parametrize(
    "text",
    ["Music therapy for her", "This improves memory", "It reduces agitation", "Treats dementia"],
)
def test_medical_claims_are_caught(text: str) -> None:
    assert makes_medical_claim(text)


def test_ordinary_reasons_pass() -> None:
    assert not makes_medical_claim("Similar to The Supremes, which Margaret loves.")
