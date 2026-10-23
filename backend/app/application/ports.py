"""Interfaces the application depends on: TasteGraph, MediaResolver, LanguageModel, repositories.

Adapters in `infrastructure/` implement these. The application never imports an adapter.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.domain.feedback import Exclusion, Feedback
from app.domain.models import EntityType, Favourite, Profile
from app.domain.runs import AgentRun, AgentStep, RunStatus
from app.domain.sessions import Session, SessionStatus

TasteSource = Literal["qloo_live", "demo_fixture"]
MediaProvider = Literal["youtube", "demo"]

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
    """An embeddable video for an item. Demo media stands in for a video in fixture mode."""

    video_id: str
    title: str
    duration_s: int
    provider: MediaProvider = "youtube"


class MediaResolver(Protocol):
    """Finds a playable, embeddable video."""

    async def resolve(self, query: str) -> PlayableMedia | None:
        """The best embeddable video for the query, or None when nothing is playable.

        Raises `UpstreamError` when the service fails, so a failure is never cached as "nothing
        playable".
        """
        ...


class LanguageModel(Protocol):
    """The one door to the LLM for structured answers (compose, interpret, extract)."""

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


class SessionRepository(Protocol):
    """Sessions with their items. Deleting a profile deletes its sessions."""

    async def add(self, session: Session) -> None:
        """Store a new session and its items."""
        ...

    async def get(self, session_id: UUID) -> Session | None:
        """One session with its items, whoever owns it. Services check ownership."""
        ...

    async def update(self, session: Session) -> None:
        """Save the session's fields and replace its items."""
        ...

    async def list_for_profile(
        self, profile_id: UUID, statuses: frozenset[SessionStatus] | None = None
    ) -> list[Session]:
        """The profile's sessions, newest first, optionally only those with these statuses."""
        ...


class FeedbackRepository(Protocol):
    """Reactions and signals, kept for learning."""

    async def add(self, feedback: Feedback) -> None:
        """Store one reaction or signal."""
        ...

    async def list_for_profile(self, profile_id: UUID) -> list[Feedback]:
        """Every reaction and signal for the profile, oldest first."""
        ...


class ExclusionRepository(Protocol):
    """Items the caregiver rejected or hid. At most one per item ref per profile."""

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
