"""Tests for the learning rules: weights, once-a-day signals, strong signals, liked and saved
states, the era window and ranking."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.feedback import Feedback, Signal
from app.domain.models import EntityType
from app.domain.policies import (
    counted_today,
    era_window,
    item_states,
    learned_weights,
    rank_key,
    signal_refs,
)

PROFILE = uuid4()
DAY = datetime(2026, 10, 24, 12, tzinfo=UTC)


def signal(ref: str, kind: Signal, at: datetime = DAY) -> Feedback:
    return Feedback(PROFILE, ref, ref.title(), kind, EntityType.ARTIST, created_at=at)


def test_weights_add_up_per_item() -> None:
    feedback = [
        signal("a", Signal.LIKED),
        signal("a", Signal.SAVED),
        signal("b", Signal.QUIZ_PICK),
        signal("c", Signal.DISLIKED),
        signal("d", Signal.JOURNAL_CONFIRMED),
    ]

    assert learned_weights(feedback) == {"a": 1.6, "b": 0.5, "c": -0.5, "d": 1.0}


def test_undo_signals_cancel_their_weight() -> None:
    feedback = [signal("a", Signal.LIKED), signal("a", Signal.UNLIKED)]

    assert learned_weights(feedback) == {"a": 0.0}


def test_opened_counts_once_a_day() -> None:
    feedback = [
        signal("a", Signal.OPENED),
        signal("a", Signal.OPENED, DAY + timedelta(hours=1)),
        signal("a", Signal.OPENED, DAY + timedelta(days=1)),
    ]

    assert learned_weights(feedback) == {"a": 0.6}
    assert counted_today(feedback, "a", Signal.OPENED, DAY)
    assert not counted_today(feedback, "a", Signal.OPENED, DAY + timedelta(days=2))


def test_strong_signals_come_newest_first() -> None:
    feedback = [
        signal("old", Signal.LIKED, DAY),
        signal("weak", Signal.OPENED, DAY + timedelta(hours=2)),
        signal("new", Signal.SAVED, DAY + timedelta(hours=1)),
    ]

    assert signal_refs(feedback) == ["new", "old"]


def test_states_follow_the_latest_like_and_save() -> None:
    feedback = [
        signal("a", Signal.LIKED, DAY),
        signal("a", Signal.UNLIKED, DAY + timedelta(minutes=1)),
        signal("b", Signal.SAVED, DAY),
        signal("c", Signal.LIKED, DAY),
        signal("c", Signal.SAVED, DAY),
    ]

    assert item_states(feedback) == {
        "b": frozenset({Signal.SAVED}),
        "c": frozenset({Signal.LIKED, Signal.SAVED}),
    }


def test_era_window_is_their_teens_and_widens_on_retry() -> None:
    assert era_window(2001) == (2014, 2022)
    assert era_window(2001, attempt=1) == (2009, 2027)


def test_rank_key_orders_by_affinity_band_then_weight_then_popularity() -> None:
    keys = {
        "strong": rank_key(0.92, 0.0, 0.1),
        "tie_but_liked": rank_key(0.88, 1.0, 0.1),
        "weaker": rank_key(0.7, 1.0, 0.9),
    }

    assert sorted(keys, key=keys.__getitem__) == ["tie_but_liked", "strong", "weaker"]
