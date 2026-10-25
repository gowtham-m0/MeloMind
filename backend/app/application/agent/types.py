"""The values the build_feed workflow passes between its nodes (docs/AGENT.md, section 2)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from app.domain.feed import ItemSource
from app.domain.feedback import Blocklist
from app.domain.models import EntityType
from app.domain.policies import era_window

ResearchOutcome = Literal["ok", "too_few", "limit_hit", "timeout", "error", "skipped"]
Tier = Literal["A", "B", "C"]

ALL_TYPES = (EntityType.ARTIST, EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK)


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
class FeedContext:
    """What `load_context` gathered. Only what the feed needs: no journal text, no keys.
    `journal_signals` are the items from confirmed journal links, newest first."""

    profile_id: UUID
    first_name: str
    birth_year: int | None
    country_code: str | None
    favourite_signals: tuple[SignalRef, ...]
    learned_signals: tuple[SignalRef, ...]
    text_favourites: tuple[str, ...]
    song_titles: tuple[str, ...]
    blocklist: Blocklist
    learned_weights: Mapping[str, float] = field(default_factory=dict)
    previous_refs: frozenset[str] = frozenset()
    previous_tags: tuple[str, ...] = ()
    journal_signals: tuple[SignalRef, ...] = ()

    @property
    def era(self) -> tuple[int, int] | None:
        """The years they were 13 to 21, when the birth year is known."""
        return era_window(self.birth_year) if self.birth_year else None

    @property
    def signals(self) -> tuple[SignalRef, ...]:
        """Learned items first (the newest taste), then journal items, then favourites."""
        taken = {signal.ref for signal in self.learned_signals + self.favourite_signals}
        journal = tuple(signal for signal in self.journal_signals if signal.ref not in taken)
        return self.learned_signals + journal + self.favourite_signals


@dataclass(frozen=True)
class Candidate:
    """An entity a tool returned this run, with the basis for its reason.

    `signal` is that basis in words ("similar to The Strokes, which you love"), and
    `because_ref`/`because_name` the item behind it, when there is one. `featured` marks the
    research agent's own best picks, which lead the "Recommended for you" row. Songs also carry
    their credited artists, the Qloo artist they were looked up for, and catalogue URLs.
    """

    entity_id: str
    name: str
    entity_type: EntityType
    source: ItemSource
    signal: str
    because_ref: str | None = None
    because_name: str | None = None
    release_year: int | None = None
    popularity: float | None = None
    affinity: float | None = None
    why: str = ""
    image_url: str | None = None
    description: str | None = None
    isbn13: str | None = None
    tags: tuple[str, ...] = ()
    external: tuple[tuple[str, str], ...] = ()
    featured: bool = False
    creator: str | None = None
    parent_ref: str | None = None
    parent_name: str | None = None
    preview_url: str | None = None
    store_url: str | None = None


@dataclass(frozen=True)
class ResearchBrief:
    """The goal and constraints given to the research agent."""

    goal: str
    tier: Tier
    per_type: int
    country_code: str | None
    popularity_min: float | None
    signals: tuple[SignalRef, ...]
    dismissed: tuple[str, ...] = ()
    tag_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class FallbackQuery:
    """One rule-based insights query. `signal_from` uses earlier results of that type as signals,
    so cold-start artists can follow popular films."""

    entity_type: EntityType
    take: int
    signal_ids: tuple[str, ...] = ()
    signal_from: EntityType | None = None
    country_code: str | None = None
    popularity_min: float | None = None
