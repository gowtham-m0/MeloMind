"""Interfaces the application depends on: TasteGraph, MediaResolver, LanguageModel, repositories.

Adapters in `infrastructure/` implement these. The application never imports an adapter.
"""

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from app.domain.models import EntityType, Favourite, Profile

TasteSource = Literal["qloo_live", "demo_fixture"]

INSIGHTS_TAKE_MAX = 50


@dataclass(frozen=True)
class EntityMatch:
    """One entity from the taste graph: a search match or an insights candidate."""

    entity_id: str
    name: str
    type: EntityType
    source: TasteSource
    release_year: int | None = None
    popularity: float | None = None
    affinity: float | None = None


@dataclass(frozen=True)
class InsightsQuery:
    """A request for recommendations of one type. Adapters send only what Qloo supports.

    `year_min`/`year_max` apply to films, TV and books only, and `country_code` (ISO 3166-1
    alpha-2) to films and TV only; adapters drop them for other types. `score_entities` limits
    the results to these IDs, each scored against the signals (the Person-mode warm-up).
    """

    entity_type: EntityType
    take: int
    signal_entities: tuple[str, ...] = ()
    signal_tags: tuple[str, ...] = ()
    age_55_plus: bool = False
    year_min: int | None = None
    year_max: int | None = None
    country_code: str | None = None
    popularity_min: float | None = None
    exclude_entities: tuple[str, ...] = ()
    exclude_tags: tuple[str, ...] = ()
    score_entities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.take <= INSIGHTS_TAKE_MAX:
            raise ValueError(f"take must be between 1 and {INSIGHTS_TAKE_MAX}")


class TasteGraph(Protocol):
    """Qloo's taste graph, live or from the demo fixtures."""

    @property
    def source(self) -> TasteSource:
        """Where results come from, for the "Demo data" or "Live Qloo" badge."""
        ...

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        """Find entities by name. Never pass a song title or a lyric."""
        ...

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        """Recommendations of one type for the given signals and filters."""
        ...


@dataclass(frozen=True)
class PlayableMedia:
    """An embeddable video for an item."""

    video_id: str
    title: str
    duration_s: int


class MediaResolver(Protocol):
    """Finds a playable, embeddable video. The adapters arrive in Phase 2."""

    async def resolve(self, query: str) -> PlayableMedia | None:
        """The best embeddable video for the query, or None when nothing is playable."""
        ...


class LanguageModel(Protocol):
    """The one door to the LLM. The adapters and structured output arrive in Phase 2."""

    async def complete(self, system: str, prompt: str) -> str:
        """A single completion. Raises on failure or timeout so callers fall back to templates."""
        ...


class ProfileRepository(Protocol):
    """Profiles and their favourites. Deleting a profile deletes its favourites."""

    async def list_for_owner(self, owner_id: UUID) -> list[Profile]:
        """Every profile the user owns, oldest first, with favourites."""
        ...

    async def get(self, profile_id: UUID) -> Profile | None:
        """One profile with its favourites, whoever owns it. Services check ownership."""
        ...

    async def add(self, profile: Profile) -> None:
        """Store a new profile and any favourites it already has."""
        ...

    async def update(self, profile: Profile) -> None:
        """Save the profile's own fields. Favourites change through their own methods."""
        ...

    async def delete(self, profile_id: UUID) -> None:
        """Delete the profile and everything that belongs to it."""
        ...

    async def add_favourite(self, favourite: Favourite) -> None:
        """Store a new favourite on its profile."""
        ...

    async def delete_favourite(self, profile_id: UUID, favourite_id: UUID) -> bool:
        """Delete one favourite of this profile. False when there was none."""
        ...
