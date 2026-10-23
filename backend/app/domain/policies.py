"""Learning rules: how feedback becomes weights and Qloo signals, the era window, ranking, and
session length.

These are heuristics chosen for this app. They are not clinically validated.
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from app.domain.feedback import Actor, Feedback, PersonSignal, Reaction

ERA_START_AGE = 13
ERA_END_AGE = 21
ERA_WIDEN_YEARS = 5
# The middle of the era window: stands in for an unknown year when finding media.
ERA_MIDDLE_AGE = 17

CAREGIVER_WEIGHTS: dict[Reaction, float] = {
    Reaction.SANG_ALONG: 1.0,
    Reaction.SMILED: 0.6,
    Reaction.CALM: 0.2,
    Reaction.NEUTRAL: 0.0,
}
PERSON_WEIGHTS: dict[PersonSignal, float] = {
    PersonSignal.CHOSE: 0.3,
    PersonSignal.LOVED: 0.6,
    PersonSignal.REPLAYED: 0.6,
    PersonSignal.SKIPPED: -0.2,
}
# Reactions that block an item instead of weighting it: `upset` hides it, `rejected` excludes it.
BLOCKING_REACTIONS = frozenset({Reaction.UPSET, Reaction.REJECTED})
SKIP_MAX_SECONDS = 15
# Items whose total weight reaches this become Qloo signals in the next plan.
SIGNAL_THRESHOLD = 0.6
# Affinities this close count as a tie, so learned weight can decide between them.
AFFINITY_BAND = 0.1

# A book has no video: it's a short conversation slot instead.
BOOK_TALK_SECONDS = 180
LENGTH_TOLERANCE = 0.1

_MEMORY_TEST = re.compile(r"\b(remember|recall)", re.IGNORECASE)
_MEDICAL_CLAIM = re.compile(
    r"\b(treat(s|ed|ing|ment)?|therap\w*|cur(e|es|ed|ing)|heal(s|ed|ing)?"
    r"|improves? (your |their |her |his )?memory|memory loss|agitation|symptoms?"
    r"|medicat\w*|diagnos\w*|dementia|alzheimer\w*)\b",
    re.IGNORECASE,
)


def era_window(birth_year: int, attempt: int = 0) -> tuple[int, int]:
    """The years they were 13 to 21, widened by 5 years on each side per fallback retry."""
    widen = ERA_WIDEN_YEARS * attempt
    return birth_year + ERA_START_AGE - widen, birth_year + ERA_END_AGE + widen


def era_middle_year(birth_year: int) -> int:
    """The year they turned 17."""
    return birth_year + ERA_MIDDLE_AGE


def skip_counts(played_s: int | None) -> bool:
    """A skip counts only when the item played for under 15 seconds."""
    return played_s is not None and played_s < SKIP_MAX_SECONDS


def feedback_weight(feedback: Feedback) -> float:
    """The weight one reaction or signal adds to its item. Blocking reactions add nothing."""
    if feedback.actor is Actor.CAREGIVER:
        return CAREGIVER_WEIGHTS.get(Reaction(feedback.kind), 0.0)
    return PERSON_WEIGHTS[PersonSignal(feedback.kind)]


def counted_today(
    feedback: Iterable[Feedback], item_ref: str, signal: PersonSignal, now: datetime
) -> bool:
    """True when the person already gave this signal for this item today (UTC)."""
    return any(
        entry.actor is Actor.PERSON
        and entry.item_ref == item_ref
        and entry.kind == signal.value
        and entry.created_at.date() == now.date()
        for entry in feedback
    )


def learned_weights(feedback: Iterable[Feedback]) -> dict[str, float]:
    """The total weight of each item ref. Each person signal counts once per item per day."""
    totals: defaultdict[str, float] = defaultdict(float)
    seen: set[tuple[str, str, object]] = set()
    for entry in feedback:
        if entry.actor is Actor.PERSON:
            key = (entry.item_ref, entry.kind, entry.created_at.date())
            if key in seen:
                continue
            seen.add(key)
        totals[entry.item_ref] += feedback_weight(entry)
    return {ref: round(weight, 2) for ref, weight in totals.items()}


def signal_refs(weights: dict[str, float]) -> list[str]:
    """Refs whose weight reaches the signal threshold, highest weight first."""
    strong = [(ref, weight) for ref, weight in weights.items() if weight >= SIGNAL_THRESHOLD]
    return [ref for ref, _ in sorted(strong, key=lambda pair: -pair[1])]


def rank_key(
    affinity: float | None, weight: float, popularity: float | None
) -> tuple[int, float, float]:
    """Sort key, smallest first: Qloo affinity (in bands), then learned weight, then popularity."""
    band = round((affinity or 0.0) / AFFINITY_BAND)
    return (-band, -weight, -(popularity or 0.0))


def age_at_release(birth_year: int, release_year: int | None) -> int | None:
    """How old they were when it came out, or None when unknown or before they were born."""
    if release_year is None or release_year < birth_year:
        return None
    return release_year - birth_year


def target_bounds(target_minutes: int) -> tuple[int, int]:
    """The shortest and longest acceptable session, in seconds: the target ± 10 %."""
    target = target_minutes * 60
    return round(target * (1 - LENGTH_TOLERANCE)), round(target * (1 + LENGTH_TOLERANCE))


def is_memory_test(prompt: str) -> bool:
    """True for a prompt that tests memory ("Do you remember…?") instead of inviting a chat."""
    return _MEMORY_TEST.search(prompt) is not None


def makes_medical_claim(text: str) -> bool:
    """True for text that mentions treatment, symptoms or a diagnosis. We make no medical claims."""
    return _MEDICAL_CLAIM.search(" ".join(text.split())) is not None
