"""The `SessionMode` strategy, and `MixMode`, the shared logic for modes built on a mix of types.

A mode decides the research brief, the rule-based fallback queries, how to relax them, and how
to pick the final mix. Adding a mode never changes the workflows or the API.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import replace
from typing import Protocol

from app.application.agent.types import (
    Candidate,
    FallbackQuery,
    PlanContext,
    ResearchBrief,
    Selection,
    Tier,
)
from app.domain.media import decade_of
from app.domain.models import EntityType
from app.domain.policies import ERA_WIDEN_YEARS

# Tier C (nothing specific): the big hits of their youth.
HIGH_POPULARITY = 0.7
RELAX_POPULARITY_STEP = 0.2
# Each fallback query asks for this many candidates per item needed, at least MIN_TAKE.
TAKE_PER_ITEM = 3
MIN_TAKE = 5
# Query order: films first, so cold-start artists can follow the era's films.
QUERY_ORDER = (EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK, EntityType.ARTIST)
SIGNAL_FROM_TOP = 3
ENGLISH = "english"


class SessionMode(Protocol):
    """One kind of session. Registered by name in the `ModeRegistry`."""

    name: str
    writes_prompts: bool
    fits_length: bool
    mix: tuple[tuple[EntityType, int], ...]

    def research_brief(self, context: PlanContext) -> ResearchBrief:
        """The goal and constraints for the research agent."""
        ...

    def fallback_queries(self, context: PlanContext) -> list[FallbackQuery]:
        """The rule-based query plan, one query per type."""
        ...

    def relax(self, queries: Sequence[FallbackQuery], attempt: int) -> list[FallbackQuery]:
        """Looser queries for fallback retry `attempt` (1 or 2)."""
        ...

    def shortfall(self, candidates: Iterable[Candidate]) -> set[EntityType]:
        """The types that still have fewer candidates than the mix needs."""
        ...

    def has_enough(self, candidates: Iterable[Candidate]) -> bool:
        """True when the candidates can fill the mix and its spares."""
        ...

    def select(self, ranked: Sequence[Candidate], context: PlanContext) -> Selection:
        """The mix in play order, plus spares, from candidates ranked best first."""
        ...


def cold_start_tier(context: PlanContext) -> Tier:
    """A: 3 or more verified favourites. B: 1–2, or any other hint. C: nothing specific."""
    favourites = len(context.favourite_signals)
    if favourites >= 3:
        return "A"
    if favourites or context.learned_signals or context.text_favourites:
        return "B"
    return "C"


def tag_hints(context: PlanContext) -> tuple[str, ...]:
    """Tag lookups worth trying: their languages other than English (a region's music and film)."""
    return tuple(
        language for language in context.languages if language.strip().casefold() != ENGLISH
    )


def era_tag(context: PlanContext) -> str:
    """The era as a tag lookup, such as "60s" for someone who was 17 in 1965."""
    return f"{decade_of(context.era_year) % 100:02d}s"


class MixMode:
    """A mode that fills a fixed mix of types, ranked by Qloo and learning, plus spares."""

    name = "mix"
    writes_prompts = True
    fits_length = True
    mix: tuple[tuple[EntityType, int], ...] = ()
    spares = 4
    min_candidates = 8

    def goal(self, context: PlanContext) -> str:
        """What the session is for, in one line."""
        raise NotImplementedError

    def popularity_floor(self, tier: Tier) -> float | None:
        """The popularity floor for the tier. Only "nothing specific" needs one."""
        return HIGH_POPULARITY if tier == "C" else None

    def research_brief(self, context: PlanContext) -> ResearchBrief:
        """The brief for the tier the profile is in."""
        tier = cold_start_tier(context)
        return ResearchBrief(
            goal=self.goal(context),
            tier=tier,
            mix=self.mix,
            spares=self.spares,
            era=context.era,
            country_code=context.country_code,
            popularity_min=self.popularity_floor(tier),
            use_age_signal=tier != "A",
            signals=context.signals,
            tag_hints=(*tag_hints(context), era_tag(context)) if tier != "A" else (),
        )

    def fallback_queries(self, context: PlanContext) -> list[FallbackQuery]:
        """One query per type in the mix, films first. Artists without an entity signal follow
        the era films and tags, never the age signal alone."""
        tier = cold_start_tier(context)
        signals = tuple(signal.ref for signal in context.signals)
        regions = tag_hints(context) if tier != "A" else ()
        counts = dict(self.mix)
        queries: list[FallbackQuery] = []
        for entity_type in QUERY_ORDER:
            if entity_type not in counts:
                continue
            query = FallbackQuery(
                entity_type=entity_type,
                take=max(counts[entity_type] * TAKE_PER_ITEM, MIN_TAKE),
                signal_ids=signals,
                tag_queries=regions,
                age_55_plus=tier != "A",
                era=context.era,
                country_code=context.country_code,
                popularity_min=self.popularity_floor(tier),
            )
            if entity_type is EntityType.ARTIST and not signals:
                query = replace(
                    query,
                    signal_from=EntityType.MOVIE,
                    tag_queries=(*regions, era_tag(context)),
                )
            queries.append(query)
        return queries

    def relax(self, queries: Sequence[FallbackQuery], attempt: int) -> list[FallbackQuery]:
        """Widen the era by 5 years per attempt; from the second attempt, also lower the
        popularity floor by 0.2."""
        widen = ERA_WIDEN_YEARS * attempt
        relaxed: list[FallbackQuery] = []
        for query in queries:
            era = None if query.era is None else (query.era[0] - widen, query.era[1] + widen)
            popularity = query.popularity_min
            if popularity is not None and attempt >= 2:
                popularity = round(max(popularity - RELAX_POPULARITY_STEP, 0.0), 2)
            relaxed.append(replace(query, era=era, popularity_min=popularity))
        return relaxed

    def shortfall(self, candidates: Iterable[Candidate]) -> set[EntityType]:
        """Types with fewer candidates than the mix needs."""
        counts: defaultdict[EntityType, int] = defaultdict(int)
        for candidate in candidates:
            counts[candidate.entity_type] += 1
        return {entity_type for entity_type, needed in self.mix if counts[entity_type] < needed}

    def has_enough(self, candidates: Iterable[Candidate]) -> bool:
        """Every type in the mix is covered, and there are at least `min_candidates`."""
        listed = list(candidates)
        return not self.shortfall(listed) and len(listed) >= self.min_candidates

    def select(self, ranked: Sequence[Candidate], context: PlanContext) -> Selection:
        """The best of each type for the mix, gaps filled by the best of any type in the mix,
        in an interleaved play order. Spares: the best leftover of each type, then by rank."""
        allowed = {entity_type for entity_type, _ in self.mix}
        pool = [candidate for candidate in ranked if candidate.entity_type in allowed]
        chosen: list[Candidate] = []
        for entity_type, count in self.mix:
            of_type = [candidate for candidate in pool if candidate.entity_type is entity_type]
            chosen.extend(self.pick(of_type, count))
        leftovers = [candidate for candidate in pool if candidate not in chosen]
        needed = sum(count for _, count in self.mix) - len(chosen)
        chosen.extend(leftovers[: max(needed, 0)])
        leftovers = [candidate for candidate in leftovers if candidate not in chosen]
        return Selection(selected=self.play_order(chosen), spares=self._spares(leftovers))

    def pick(self, candidates: list[Candidate], count: int) -> list[Candidate]:
        """The `count` best candidates of one type."""
        return candidates[:count]

    def play_order(self, chosen: list[Candidate]) -> list[Candidate]:
        """Interleave the types, in mix order, so the session moves between them."""
        queues = {
            entity_type: [candidate for candidate in chosen if candidate.entity_type is entity_type]
            for entity_type, _ in self.mix
        }
        ordered: list[Candidate] = []
        while any(queues.values()):
            for queue in queues.values():
                if queue:
                    ordered.append(queue.pop(0))
        return ordered

    def _spares(self, leftovers: list[Candidate]) -> list[Candidate]:
        spares: list[Candidate] = []
        for entity_type, _ in self.mix:
            best = next((c for c in leftovers if c.entity_type is entity_type), None)
            if best is not None:
                spares.append(best)
        rest = [candidate for candidate in leftovers if candidate not in spares]
        return (spares + rest)[: max(self.spares, len(spares))]
