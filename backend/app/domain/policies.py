"""Learning rules: how signals become weights and Qloo signals, which items show as liked or
saved, the throwback era and ranking. Simple, explainable heuristics, chosen for this app."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from app.domain.feedback import Feedback, Signal

ERA_START_AGE = 13
ERA_END_AGE = 21
ERA_WIDEN_YEARS = 5

SIGNAL_WEIGHTS: dict[Signal, float] = {
    Signal.LIKED: 1.0,
    Signal.UNLIKED: -1.0,
    Signal.SAVED: 0.6,
    Signal.UNSAVED: -0.6,
    Signal.OPENED: 0.3,
    Signal.QUIZ_PICK: 0.6,
    Signal.JOURNAL_CONFIRMED: 1.0,
    Signal.DISLIKED: -0.5,
    Signal.NOT_INTERESTED: 0.0,
}
# Signals that count at most once per item per day, so repeated taps don't inflate a weight.
ONCE_A_DAY = frozenset({Signal.OPENED})
# Items whose total weight reaches this become Qloo signals in the next feed. A single quiz pick
# or save is enough; an open (0.3) needs a second one on another day.
SIGNAL_THRESHOLD = 0.6
# Affinities this close count as a tie, so learned weight can decide between them.
AFFINITY_BAND = 0.1


def era_window(birth_year: int, attempt: int = 0) -> tuple[int, int]:
    """The years they were 13 to 21, widened by 5 years on each side per retry."""
    widen = ERA_WIDEN_YEARS * attempt
    return birth_year + ERA_START_AGE - widen, birth_year + ERA_END_AGE + widen


def counted_today(
    feedback: Iterable[Feedback], item_ref: str, signal: Signal, now: datetime
) -> bool:
    """True when this signal was already given for this item today (UTC)."""
    return any(
        entry.item_ref == item_ref
        and entry.kind is signal
        and entry.created_at.date() == now.date()
        for entry in feedback
    )


def _counted(feedback: Iterable[Feedback]) -> list[Feedback]:
    """The feedback that counts, dropping repeats of once-a-day signals."""
    seen: set[tuple[str, Signal, object]] = set()
    kept: list[Feedback] = []
    for entry in feedback:
        if entry.kind in ONCE_A_DAY:
            key = (entry.item_ref, entry.kind, entry.created_at.date())
            if key in seen:
                continue
            seen.add(key)
        kept.append(entry)
    return kept


def learned_weights(feedback: Iterable[Feedback]) -> dict[str, float]:
    """The total weight of each item ref."""
    totals: defaultdict[str, float] = defaultdict(float)
    for entry in _counted(feedback):
        totals[entry.item_ref] += SIGNAL_WEIGHTS[entry.kind]
    return {ref: round(weight, 2) for ref, weight in totals.items()}


def signal_refs(feedback: Iterable[Feedback]) -> list[str]:
    """Refs whose weight reaches the threshold, newest activity first, so the feed follows
    recent taste."""
    entries = list(feedback)
    weights = learned_weights(entries)
    last_seen: dict[str, datetime] = {}
    for entry in entries:
        if entry.item_ref not in last_seen or entry.created_at > last_seen[entry.item_ref]:
            last_seen[entry.item_ref] = entry.created_at
    strong = [ref for ref, weight in weights.items() if weight >= SIGNAL_THRESHOLD]
    return sorted(strong, key=lambda ref: last_seen[ref], reverse=True)


def item_states(feedback: Iterable[Feedback]) -> dict[str, frozenset[Signal]]:
    """Which items are currently liked or saved: the latest of like/unlike and save/unsave
    wins. Returned as `{ref: {LIKED, SAVED}}`, only for items with at least one."""
    liked: dict[str, bool] = {}
    saved: dict[str, bool] = {}
    for entry in sorted(feedback, key=lambda item: item.created_at):
        if entry.kind in (Signal.LIKED, Signal.UNLIKED):
            liked[entry.item_ref] = entry.kind is Signal.LIKED
        elif entry.kind in (Signal.SAVED, Signal.UNSAVED):
            saved[entry.item_ref] = entry.kind is Signal.SAVED
    states: dict[str, frozenset[Signal]] = {}
    for ref in set(liked) | set(saved):
        state = {Signal.LIKED} if liked.get(ref) else set()
        if saved.get(ref):
            state.add(Signal.SAVED)
        if state:
            states[ref] = frozenset(state)
    return states


def rank_key(
    affinity: float | None, weight: float, popularity: float | None
) -> tuple[int, float, float]:
    """Sort key, smallest first: Qloo affinity (in bands), then learned weight, then popularity."""
    band = round((affinity or 0.0) / AFFINITY_BAND)
    return (-band, -weight, -(popularity or 0.0))
