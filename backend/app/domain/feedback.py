"""Feedback from the caregiver and the person, and the items they've blocked."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.models import EntityType, utc_now
from app.domain.names import normalise_name
from app.domain.sessions import is_favourite_ref


class Actor(StrEnum):
    """Who gave the feedback."""

    CAREGIVER = "caregiver"
    PERSON = "person"


class Reaction(StrEnum):
    """What the caregiver saw. Only the caregiver can hide (`upset`) or reject an item."""

    SANG_ALONG = "sang_along"
    SMILED = "smiled"
    CALM = "calm"
    NEUTRAL = "neutral"
    UPSET = "upset"
    REJECTED = "rejected"


class PersonSignal(StrEnum):
    """What the person did in Person mode. A quick skip only lowers an item's ranking."""

    CHOSE = "chose"
    LOVED = "loved"
    REPLAYED = "replayed"
    SKIPPED = "skipped"


@dataclass
class Feedback:
    """One reaction or signal for an item. `kind` is a `Reaction` or a `PersonSignal` value."""

    profile_id: UUID
    item_ref: str
    title: str
    actor: Actor
    kind: str
    entity_type: EntityType | None = None
    session_id: UUID | None = None
    note: str | None = None
    played_s: int | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


class ExclusionKind(StrEnum):
    """Why an item is blocked. Both kinds keep it out of sessions and Person mode."""

    REJECTED = "rejected"
    HIDDEN = "hidden"


@dataclass
class Exclusion:
    """An item that must not appear again for this profile. Hidden items wait for review."""

    profile_id: UUID
    entity_ref: str
    title: str
    kind: ExclusionKind
    needs_review: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Blocklist:
    """Everything a profile has blocked, checked in code wherever items are chosen or shown.

    Items with a Qloo ID are matched by ID. Items without one (`fav:` refs) are also matched by
    their normalised title, so a typed favourite can't slip back in under a new ID.
    """

    refs: frozenset[str] = frozenset()
    titles: frozenset[str] = frozenset()

    @classmethod
    def from_exclusions(cls, exclusions: Iterable[Exclusion]) -> "Blocklist":
        """The blocklist for these exclusions, of either kind."""
        entries = list(exclusions)
        return cls(
            refs=frozenset(entry.entity_ref for entry in entries),
            titles=frozenset(normalise_name(entry.title) for entry in entries),
        )

    def blocks(self, ref: str, title: str) -> bool:
        """True when the item must not appear."""
        if ref in self.refs:
            return True
        return is_favourite_ref(ref) and normalise_name(title) in self.titles

    @property
    def qloo_ids(self) -> tuple[str, ...]:
        """The blocked refs Qloo knows, for `filter.exclude.entities`."""
        return tuple(sorted(ref for ref in self.refs if not is_favourite_ref(ref)))
