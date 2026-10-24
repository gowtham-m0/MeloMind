"""What the user does with items (likes, saves, opens, dismisses) and what they've excluded."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.feed import is_favourite_ref
from app.domain.models import EntityType, utc_now
from app.domain.names import normalise_name


class Signal(StrEnum):
    """One thing the user did with an item. `not_interested` excludes it (rule 3)."""

    LIKED = "liked"
    UNLIKED = "unliked"
    SAVED = "saved"
    UNSAVED = "unsaved"
    OPENED = "opened"
    QUIZ_PICK = "quiz_pick"
    JOURNAL_CONFIRMED = "journal_confirmed"
    DISLIKED = "disliked"
    NOT_INTERESTED = "not_interested"


@dataclass
class Feedback:
    """One signal for an item, kept for learning. `platform` is the link used for `opened`."""

    profile_id: UUID
    item_ref: str
    title: str
    kind: Signal
    entity_type: EntityType | None = None
    platform: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Exclusion:
    """An item marked "not interested". It never appears again until the user undoes it."""

    profile_id: UUID
    entity_ref: str
    title: str
    entity_type: EntityType | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Blocklist:
    """Everything a profile excluded, checked in code wherever items are chosen or shown.

    Items with a Qloo ID are matched by ID. Items without one (`fav:` refs) are also matched by
    their normalised title, so a typed favourite can't slip back in under a new ID.
    """

    refs: frozenset[str] = frozenset()
    titles: frozenset[str] = frozenset()

    @classmethod
    def from_exclusions(cls, exclusions: Iterable[Exclusion]) -> "Blocklist":
        """The blocklist for these exclusions."""
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
        """The excluded refs Qloo knows, for `filter.exclude.entities`."""
        return tuple(sorted(ref for ref in self.refs if not is_favourite_ref(ref)))
