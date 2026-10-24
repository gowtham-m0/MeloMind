"""The feed: a hero pick and rows of items, each with its reason, image and platform links."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from app.domain.models import EntityType, Favourite, FavouriteKind, utc_now

FAVOURITE_REF_PREFIX = "fav:"
SONG_REF_PREFIX = "song:"

LinkKind = Literal["direct", "search"]
RowPlacement = Literal["main", "rail"]
ImageAspect = Literal["square", "poster"]


class ItemSource(StrEnum):
    """Where an item came from (rule 1: never invent a recommendation)."""

    QLOO_LIVE = "qloo_live"
    DEMO_FIXTURE = "demo_fixture"
    FAVOURITE = "favourite"
    # A song of a Qloo-picked artist, looked up in Apple's catalogue (the pick is Qloo's).
    SONG_CATALOGUE = "song_catalogue"


def favourite_ref(favourite: Favourite) -> str:
    """The ref of a favourite: its Qloo ID when verified, else `fav:<id>`."""
    return favourite.qloo_id or f"{FAVOURITE_REF_PREFIX}{favourite.id}"


def is_favourite_ref(ref: str) -> bool:
    """True for a favourite that Qloo doesn't know (`fav:<id>`)."""
    return ref.startswith(FAVOURITE_REF_PREFIX)


def song_ref(track_id: str) -> str:
    """The ref of a song card: `song:<catalogue track ID>`."""
    return f"{SONG_REF_PREFIX}{track_id}"


def is_song_ref(ref: str) -> bool:
    """True for a song card, which Qloo doesn't know."""
    return ref.startswith(SONG_REF_PREFIX)


def is_qloo_ref(ref: str) -> bool:
    """True when the ref is a Qloo entity ID that may be sent to Qloo."""
    return not is_favourite_ref(ref) and not is_song_ref(ref)


def entity_type_of(kind: FavouriteKind) -> EntityType:
    """The card type of a favourite. A song shows as its singer, an artist card."""
    return EntityType.ARTIST if kind is FavouriteKind.SONG else EntityType(kind.value)


def image_aspect(entity_type: EntityType) -> ImageAspect:
    """Artists and songs are square; films, TV and books are posters."""
    return "square" if entity_type in (EntityType.ARTIST, EntityType.SONG) else "poster"


@dataclass(frozen=True)
class PlatformLink:
    """Where to find an item. A `search` link is labelled "Search on …" (rule 5)."""

    platform: str
    label: str
    url: str
    kind: LinkKind


@dataclass(frozen=True)
class FeedItem:
    """One card. `because_of_ref` and `because_of_title` name the signal behind it (rule 2).

    Songs also carry `creator` (the credited artists), `parent_ref` and `parent_title` (the Qloo
    artist the song was looked up for: excluding the artist removes its songs, and liking the
    song also steers by the artist) and `preview_url` (Apple's 30-second preview, streamed only
    when the user taps play).
    """

    ref: str
    title: str
    entity_type: EntityType
    source: ItemSource
    reason: str
    because_of_ref: str | None = None
    because_of_title: str | None = None
    year: int | None = None
    image_url: str | None = None
    affinity: float | None = None
    popularity: float | None = None
    tags: tuple[str, ...] = ()
    description: str | None = None
    links: tuple[PlatformLink, ...] = ()
    creator: str | None = None
    parent_ref: str | None = None
    parent_title: str | None = None
    preview_url: str | None = None

    @property
    def image_aspect(self) -> ImageAspect:
        """The card shape for this item's image."""
        return image_aspect(self.entity_type)


@dataclass(frozen=True)
class FeedRow:
    """A titled row of items. `rail` rows show in the right rail (cross-culture picks)."""

    key: str
    title: str
    items: tuple[FeedItem, ...]
    subtitle: str = ""
    placement: RowPlacement = "main"


class FeedStatus(StrEnum):
    """Whether the feed is still being built."""

    BUILDING = "building"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Feed:
    """A saved snapshot of the home screen. `stale` is set when feedback arrives after it."""

    profile_id: UUID
    agent_run_id: UUID
    status: FeedStatus = FeedStatus.BUILDING
    hero: FeedItem | None = None
    rows: list[FeedRow] = field(default_factory=list)
    summary: str = ""
    taste_tags: tuple[str, ...] = ()
    stale: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def items(self) -> list[FeedItem]:
        """Every item, hero first, in row order."""
        found = [self.hero] if self.hero else []
        for row in self.rows:
            found.extend(row.items)
        return found

    def find(self, ref: str) -> FeedItem | None:
        """The item with this ref, if the feed shows it."""
        return next((item for item in self.items() if item.ref == ref), None)

    def without(self, ref: str) -> bool:
        """Remove an item everywhere at once (a "not interested"). True when it was there."""
        removed = self.hero is not None and self.hero.ref == ref
        if removed:
            self.hero = None
        rows: list[FeedRow] = []
        for row in self.rows:
            kept = tuple(item for item in row.items if item.ref != ref)
            removed = removed or len(kept) != len(row.items)
            rows.append(replace(row, items=kept) if len(kept) != len(row.items) else row)
        self.rows = [row for row in rows if row.items]
        return removed
