"""Profiles and favourites: the core entities, with no framework imports."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

BIRTH_YEAR_MIN = 1900


def birth_year_max() -> int:
    """The latest allowed birth year: the current year."""
    return datetime.now(UTC).year


class EntityType(StrEnum):
    """The kinds of card we show. All but `SONG` are Qloo types. Qloo has no songs: a song card
    is a catalogue lookup for an artist Qloo picked, and never goes to Qloo."""

    ARTIST = "artist"
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    BOOK = "book"
    SONG = "song"


class FavouriteKind(StrEnum):
    """What the user can add as a favourite. A song is stored as text plus its singer."""

    ARTIST = "artist"
    SONG = "song"
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    BOOK = "book"


def search_type_for(kind: FavouriteKind) -> EntityType:
    """The Qloo type to search for a favourite. A song is searched by its singer, not its title."""
    if kind is FavouriteKind.SONG:
        return EntityType.ARTIST
    return EntityType(kind.value)


def utc_now() -> datetime:
    """The current time in UTC."""
    return datetime.now(UTC)


@dataclass
class Favourite:
    """Something the user loves. Verified favourites carry a Qloo ID and become signals."""

    profile_id: UUID
    name: str
    kind: FavouriteKind
    qloo_id: str | None = None
    song_title: str | None = None
    image_url: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def verified(self) -> bool:
        """True when the user picked a Qloo match, so it can be used as a signal."""
        return self.qloo_id is not None


@dataclass
class Profile:
    """One taste profile of a user, Netflix-style. Only the minimum personal data."""

    owner_id: UUID
    display_name: str
    birth_year: int | None = None
    country_code: str | None = None
    places_lived: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    is_demo: bool = False
    favourites: list[Favourite] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class DemoFavouriteSpec:
    """A sample favourite, by name only. The demo seed resolves it through taste search."""

    name: str
    kind: FavouriteKind
    song_title: str | None = None


@dataclass(frozen=True)
class DemoLinkSpec:
    """A sample journal link by name: an item (resolved through taste search) or a place."""

    name: str
    kind: str


@dataclass(frozen=True)
class DemoJournalSpec:
    """A sample journal entry, dated `days_ago` before the seed, with its confirmed links."""

    days_ago: int
    text: str
    mood: str | None
    links: tuple[DemoLinkSpec, ...]


@dataclass(frozen=True)
class DemoProfileSpec:
    """A sample profile the demo seed creates for each new user, with a few things it already
    liked and one it isn't interested in, so the demo starts with learned taste."""

    key: str
    display_name: str
    birth_year: int | None
    country_code: str | None
    places_lived: tuple[str, ...]
    languages: tuple[str, ...]
    favourites: tuple[DemoFavouriteSpec, ...]
    likes: tuple[DemoFavouriteSpec, ...] = ()
    not_interested: tuple[DemoFavouriteSpec, ...] = ()
    journal: tuple[DemoJournalSpec, ...] = ()
