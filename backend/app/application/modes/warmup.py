"""`warmup`: the Person-mode "this or that" set. About 12 varied, well-known, playable items.

It has no prompts, because Person mode never shows them, and no target length.
"""

from app.application.agent.types import Candidate, PlanContext, Tier
from app.application.modes.base import HIGH_POPULARITY, MixMode
from app.domain.media import decade_of
from app.domain.models import EntityType


class WarmupMode(MixMode):
    """5 artists, 4 films and 3 TV shows across the decades of their youth. No books: every
    item must be playable."""

    name = "warmup"
    writes_prompts = False
    fits_length = False
    mix = (
        (EntityType.ARTIST, 5),
        (EntityType.MOVIE, 4),
        (EntityType.TV_SHOW, 3),
    )
    spares = 4
    min_candidates = 12

    def goal(self, context: PlanContext) -> str:
        """A warm-up set."""
        return (
            f"About 12 varied, well-known songs, films and TV shows from {context.first_name}'s "
            "youth, for a this-or-that warm-up."
        )

    def popularity_floor(self, tier: Tier) -> float | None:
        """Always well known, whatever the family gave."""
        return HIGH_POPULARITY

    def pick(self, candidates: list[Candidate], count: int) -> list[Candidate]:
        """The best of one type, one per decade first, so the pairs feel different."""
        picked: list[Candidate] = []
        decades: set[int | None] = set()
        for candidate in candidates:
            decade = decade_of(candidate.release_year) if candidate.release_year else None
            if decade not in decades:
                picked.append(candidate)
                decades.add(decade)
        rest = [candidate for candidate in candidates if candidate not in picked]
        return (picked + rest)[:count]
