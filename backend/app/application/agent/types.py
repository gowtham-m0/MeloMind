"""The values the plan_session workflow passes between its nodes (docs/AGENT.md, section 2)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from app.domain.feedback import Blocklist
from app.domain.models import EntityType
from app.domain.policies import era_middle_year, era_window
from app.domain.sessions import ItemSource, SessionItem

ResearchOutcome = Literal["ok", "too_few", "limit_hit", "timeout", "error", "skipped"]
Tier = Literal["A", "B", "C"]


@dataclass(frozen=True)
class SignalRef:
    """Something that can steer Qloo: a verified favourite, a learned item or a tag."""

    ref: str
    name: str
    entity_type: EntityType | None = None
    learned: bool = False

    @property
    def is_tag(self) -> bool:
        """True for a tag signal, which goes in `signal.interests.tags`."""
        return self.entity_type is None


@dataclass(frozen=True)
class PlanContext:
    """What `load_context` gathered. Only what the plan needs: no notes, no health data."""

    profile_id: UUID
    first_name: str
    birth_year: int
    country_code: str | None
    places: tuple[str, ...]
    languages: tuple[str, ...]
    favourite_signals: tuple[SignalRef, ...]
    learned_signals: tuple[SignalRef, ...]
    text_favourites: tuple[str, ...]
    song_titles: tuple[str, ...]
    blocklist: Blocklist
    learned_weights: Mapping[str, float] = field(default_factory=dict)
    target_minutes: int = 20

    @property
    def era(self) -> tuple[int, int]:
        """The years they were 13 to 21."""
        return era_window(self.birth_year)

    @property
    def era_year(self) -> int:
        """The year they turned 17: stands in for an unknown year when finding media."""
        return era_middle_year(self.birth_year)

    @property
    def signals(self) -> tuple[SignalRef, ...]:
        """Favourites first, then learned items."""
        return self.favourite_signals + self.learned_signals


@dataclass(frozen=True)
class Candidate:
    """An entity a tool returned this run, with the basis for its reason (`signal`)."""

    entity_id: str
    name: str
    entity_type: EntityType
    source: ItemSource
    signal: str
    release_year: int | None = None
    popularity: float | None = None
    affinity: float | None = None
    why: str = ""


@dataclass(frozen=True)
class PlannedItem:
    """A session item with its place in the ranking (0 is best)."""

    item: SessionItem
    rank: int


@dataclass(frozen=True)
class ResearchBrief:
    """The goal and constraints the mode gives the research agent."""

    goal: str
    tier: Tier
    mix: tuple[tuple[EntityType, int], ...]
    spares: int
    era: tuple[int, int]
    country_code: str | None
    popularity_min: float | None
    use_age_signal: bool
    signals: tuple[SignalRef, ...]
    tag_hints: tuple[str, ...] = ()

    @property
    def item_count(self) -> int:
        """How many items the session needs, before spares."""
        return sum(count for _, count in self.mix)


@dataclass(frozen=True)
class FallbackQuery:
    """One rule-based insights query. `signal_from` uses earlier results of that type as signals,
    so cold-start artists can follow the era's films."""

    entity_type: EntityType
    take: int
    signal_ids: tuple[str, ...] = ()
    tag_queries: tuple[str, ...] = ()
    signal_from: EntityType | None = None
    age_55_plus: bool = False
    era: tuple[int, int] | None = None
    country_code: str | None = None
    popularity_min: float | None = None


@dataclass(frozen=True)
class Selection:
    """The mode's picks in play order, plus spares best first."""

    selected: list[Candidate]
    spares: list[Candidate]
