"""Interfaces the application depends on: TasteGraph, MediaResolver, LanguageModel, repositories.

Adapters in `infrastructure/` implement these. The application never imports an adapter.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.domain.feed import Feed, FeedItem
from app.domain.feedback import Exclusion, Feedback
from app.domain.models import EntityType, Favourite, Profile
from app.domain.runs import AgentRun, AgentStep, RunStatus

TasteSource = Literal["qloo_live", "demo_fixture"]
MediaProvider = Literal["youtube", "demo"]

INSIGHTS_TAKE_MAX = 50


@dataclass(frozen=True)
class EntityMatch:
    """One entity from the taste graph: a search match or an insights candidate.

    `external` maps a platform (`spotify`, `netflix`, `imdb`, `goodreads`…) to its ID there, and
    `tags` holds up to a few tag names, genres first.
    """

    entity_id: str
    name: str
    type: EntityType
    source: TasteSource
    release_year: int | None = None
    popularity: float | None = None
    affinity: float | None = None
    image_url: str | None = None
    description: str | None = None
    isbn13: str | None = None
    tags: tuple[str, ...] = ()
    external: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class InsightsQuery:
    """A request for recommendations of one type. Adapters send only what Qloo supports.

    `year_min`/`year_max` apply to films, TV and books only, and `country_code` (ISO 3166-1
    alpha-2) to films and TV only; adapters drop them for other types. `score_entities` limits
    the results to these IDs, each scored against the signals (the taste quiz).
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


@dataclass(frozen=True)
class TagMatch:
    """A Qloo tag (genre, region…) whose ID can be a `signal.interests.tags` signal."""

    tag_id: str
    name: str


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

    async def tags(self, query: str, take: int = 5) -> list[TagMatch]:
        """Tags whose name matches the query, such as a genre or a region."""
        ...


@dataclass(frozen=True)
class PlayableMedia:
    """An embeddable video for an item's optional preview."""

    video_id: str
    title: str
    duration_s: int
    provider: MediaProvider = "youtube"


class MediaResolver(Protocol):
    """Finds a playable, embeddable video for the optional preview."""

    async def resolve(self, query: str) -> PlayableMedia | None:
        """The best embeddable video for the query, or None when nothing is playable.

        Raises `UpstreamError` when the service fails, so a failure is never cached as "nothing
        playable".
        """
        ...


class LanguageModel(Protocol):
    """The one door to the LLM for structured answers (explain, interpret, extract)."""

    async def structured[SchemaT: BaseModel](
        self, system: str, prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        """An answer parsed into `schema`. Raises on failure, timeout or invalid output, so
        callers fall back to templates."""
        ...


@dataclass(frozen=True)
class ChatModels:
    """The research agent's tool-calling chat models: the main one and an optional fallback."""

    primary: BaseChatModel
    fallback: BaseChatModel | None = None


class ProfileRepository(Protocol):
    """Profiles and their favourites. Deleting a profile deletes everything it owns."""

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


class FeedRepository(Protocol):
    """Feed snapshots. Deleting a profile deletes its feeds."""

    async def add(self, feed: Feed) -> None:
        """Store a new feed (usually while it's still building)."""
        ...

    async def get(self, feed_id: UUID) -> Feed | None:
        """One feed, whoever owns it. Services check ownership."""
        ...

    async def update(self, feed: Feed) -> None:
        """Save the feed's status, items and flags."""
        ...

    async def latest(self, profile_id: UUID, done_only: bool = False) -> Feed | None:
        """The profile's newest feed, or its newest finished one."""
        ...


class CatalogRepository(Protocol):
    """Every item the app has shown, by ref, so details and the library work after the feed
    moves on. Holds Qloo data on the server only, like the cache."""

    async def put_many(self, items: list[FeedItem]) -> None:
        """Store or refresh these items."""
        ...

    async def get_many(self, refs: list[str]) -> dict[str, FeedItem]:
        """The known items among these refs."""
        ...


class FeedbackRepository(Protocol):
    """Signals, kept for learning."""

    async def add(self, feedback: Feedback) -> None:
        """Store one signal."""
        ...

    async def list_for_profile(self, profile_id: UUID) -> list[Feedback]:
        """Every signal for the profile, oldest first."""
        ...


class ExclusionRepository(Protocol):
    """Items marked "not interested". At most one per item ref per profile."""

    async def save(self, exclusion: Exclusion) -> None:
        """Store an exclusion, replacing any with the same ID."""
        ...

    async def list_for_profile(self, profile_id: UUID) -> list[Exclusion]:
        """The profile's exclusions, oldest first."""
        ...

    async def delete(self, profile_id: UUID, exclusion_id: UUID) -> bool:
        """Delete one exclusion. False when the profile has no such exclusion."""
        ...


class AgentRunRepository(Protocol):
    """Agent runs and their logs, which the frontend polls."""

    async def add(self, run: AgentRun) -> None:
        """Store a new run."""
        ...

    async def get(self, run_id: UUID) -> AgentRun | None:
        """One run with its log, whoever owns it. Services check ownership."""
        ...

    async def append_step(self, run_id: UUID, step: AgentStep) -> None:
        """Add one entry to the run's log."""
        ...

    async def finish(self, run_id: UUID, status: RunStatus, result: dict[str, Any] | None) -> None:
        """Mark the run done or failed, with a small summary."""
        ...


@dataclass(frozen=True)
class MediaCacheEntry:
    """A cached media lookup. `media` is None when nothing playable was found."""

    media: PlayableMedia | None
    cached_at: datetime


class MediaCacheRepository(Protocol):
    """Media lookups by query, so each costs YouTube quota once (`media_cache`)."""

    async def get(self, query_key: str) -> MediaCacheEntry | None:
        """The cached lookup for the query, or None when it was never looked up."""
        ...

    async def put(self, query_key: str, media: PlayableMedia | None) -> None:
        """Remember a lookup's result, including "nothing playable"."""
        ...


@dataclass(frozen=True)
class QlooCacheEntry:
    """Cached, already parsed Qloo results for one request."""

    rows: list[dict[str, Any]]
    cached_at: datetime


class QlooCacheRepository(Protocol):
    """Qloo results on the server only (`qloo_cache`), never in the repo."""

    async def get(self, cache_key: str) -> QlooCacheEntry | None:
        """The cached results for the request, or None."""
        ...

    async def put(self, cache_key: str, rows: list[dict[str, Any]]) -> None:
        """Remember the results for the request."""
        ...
