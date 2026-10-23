"""Sessions, their items and the Person-mode shelf, with no framework imports."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.models import EntityType, Favourite, FavouriteKind, utc_now

FAVOURITE_REF_PREFIX = "fav:"


class SessionStatus(StrEnum):
    """Where a session is in its life. A warm-up set stops at `approved`."""

    PLANNING = "planning"
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


_NEXT_STATUSES: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.PLANNING: frozenset({SessionStatus.DRAFT, SessionStatus.FAILED}),
    SessionStatus.DRAFT: frozenset({SessionStatus.APPROVED}),
    SessionStatus.APPROVED: frozenset({SessionStatus.IN_PROGRESS}),
    SessionStatus.IN_PROGRESS: frozenset({SessionStatus.COMPLETED}),
    SessionStatus.COMPLETED: frozenset(),
    SessionStatus.FAILED: frozenset(),
}

# Statuses whose items the caregiver has approved, so they can reach Person mode.
APPROVED_STATUSES = frozenset(
    {SessionStatus.APPROVED, SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED}
)

WARMUP_MODE = "warmup"


class ItemSource(StrEnum):
    """Where an item came from (rule 9: never invent a recommendation)."""

    QLOO_LIVE = "qloo_live"
    DEMO_FIXTURE = "demo_fixture"
    FAVOURITE = "favourite"


class ShelfOrigin(StrEnum):
    """Why an item is on the Person-mode shelf."""

    FAVOURITE = "favourite"
    SESSION = "session"
    WARMUP = "warmup"


@dataclass(frozen=True)
class MediaRef:
    """A playable video for an item. `provider` is `youtube`, or `demo` in fixture mode."""

    provider: str
    ref: str
    duration_s: int
    title: str


@dataclass
class SessionItem:
    """One thing to play or talk about in a session.

    `ref` is the Qloo entity ID, or `fav:<id>` for a favourite with none. `signal` names what led
    to the item (a favourite, a tag, the era), the basis for its reason. Books have no media: they
    are a short conversation slot instead.
    """

    ref: str
    title: str
    entity_type: EntityType
    source: ItemSource
    reason: str = ""
    signal: str = ""
    position: int = 0
    release_year: int | None = None
    age_at_release: int | None = None
    prompt: str | None = None
    media: MediaRef | None = None
    duration_s: int = 0
    id: UUID = field(default_factory=uuid4)

    @property
    def playable(self) -> bool:
        """True when the item has a video to play."""
        return self.media is not None


@dataclass
class Session:
    """A planned session, or a warm-up set, for one profile."""

    profile_id: UUID
    mode: str
    target_minutes: int
    status: SessionStatus = SessionStatus.PLANNING
    items: list[SessionItem] = field(default_factory=list)
    agent_run_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def total_duration_s(self) -> int:
        """The length of all items together."""
        return sum(item.duration_s for item in self.items)

    @property
    def is_warmup(self) -> bool:
        """True for the Person-mode warm-up set."""
        return self.mode == WARMUP_MODE

    def can_move_to(self, status: SessionStatus) -> bool:
        """True when the status change is allowed. A warm-up set never goes past `approved`."""
        if self.is_warmup and status in (SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED):
            return False
        return status in _NEXT_STATUSES[self.status]

    def renumber(self) -> None:
        """Set each item's position from its place in the list."""
        for position, item in enumerate(self.items):
            item.position = position


@dataclass(frozen=True)
class ShelfItem:
    """A card in Person mode. It never carries a reason or a prompt. `kind` is what the card's
    icon shows, so a favourite song is a song, not its singer."""

    ref: str
    title: str
    kind: FavouriteKind
    release_year: int | None
    media: MediaRef
    origin: ShelfOrigin

    @property
    def decade(self) -> int | None:
        """The decade it came out in, for the card's colour."""
        return None if self.release_year is None else self.release_year // 10 * 10

    @classmethod
    def from_item(cls, item: SessionItem, origin: ShelfOrigin) -> "ShelfItem | None":
        """The card for an approved session item, or None when it has nothing to play."""
        if item.media is None:
            return None
        return cls(
            ref=item.ref,
            title=item.title,
            kind=FavouriteKind(item.entity_type.value),
            release_year=item.release_year,
            media=item.media,
            origin=origin,
        )


def favourite_ref(favourite: Favourite) -> str:
    """A favourite's stable ref: its Qloo ID, or `fav:<id>`. A song is never its singer's ID."""
    if favourite.qloo_id and favourite.kind is not FavouriteKind.SONG:
        return favourite.qloo_id
    return f"{FAVOURITE_REF_PREFIX}{favourite.id}"


def is_favourite_ref(ref: str) -> bool:
    """True for a `fav:<id>` ref, which Qloo doesn't know."""
    return ref.startswith(FAVOURITE_REF_PREFIX)
