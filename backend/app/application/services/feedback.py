"""Use cases for feedback: the caregiver's reactions and the person's Person-mode signals.

Everything is stored with its actor, for learning. `rejected` adds an exclusion; `upset` hides the
item and queues it for review. Person signals count only for items on the shelf, a skip only
under 15 seconds, and each signal once per item per day.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports import FeedbackRepository, SessionRepository
from app.application.services.exclusions import ExclusionService
from app.application.services.profiles import ProfileService
from app.application.services.sessions import SessionService
from app.application.services.shelf import ShelfService
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.domain.feedback import Actor, ExclusionKind, Feedback, PersonSignal, Reaction
from app.domain.models import EntityType, Profile, search_type_for, utc_now
from app.domain.policies import counted_today, skip_counts
from app.domain.sessions import SessionStatus, ShelfItem, favourite_ref

NOTE_MAX = 300

_REACTION_EFFECTS = {
    Reaction.SANG_ALONG: "Noted: sang along. More like this next time.",
    Reaction.SMILED: "Noted: smiled. More like this next time.",
    Reaction.CALM: "Noted: calm.",
    Reaction.NEUTRAL: "Noted.",
    Reaction.UPSET: "Hidden. You can review it later.",
    Reaction.REJECTED: "Rejected. It won't be suggested again.",
}
_SIGNAL_EFFECTS = {
    PersonSignal.CHOSE: "Choice noted.",
    PersonSignal.LOVED: "♥ noted.",
    PersonSignal.REPLAYED: "Replay noted.",
    PersonSignal.SKIPPED: "Skip noted: it will rank a little lower.",
}
_NOT_REACTABLE = frozenset({SessionStatus.PLANNING, SessionStatus.FAILED})


@dataclass(frozen=True)
class FeedbackEffect:
    """Whether the feedback counted, and what it changes, in plain English."""

    counted: bool
    effect: str


class FeedbackService:
    """Stores reactions and signals. Only the caregiver can hide or reject an item."""

    def __init__(
        self,
        profiles: ProfileService,
        sessions: SessionService,
        session_store: SessionRepository,
        feedback: FeedbackRepository,
        exclusions: ExclusionService,
        shelf: ShelfService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._profiles = profiles
        self._sessions = sessions
        self._session_store = session_store
        self._feedback = feedback
        self._exclusions = exclusions
        self._shelf = shelf
        self._clock = clock

    async def react_to_item(
        self,
        owner_id: UUID,
        session_id: UUID,
        item_id: UUID,
        reaction: Reaction,
        note: str | None = None,
    ) -> FeedbackEffect:
        """The caregiver's reaction to one item of a session."""
        session = await self._sessions.get(owner_id, session_id)
        if session.status in _NOT_REACTABLE:
            raise ConflictError("This session has nothing to react to.")
        item = next((item for item in session.items if item.id == item_id), None)
        if item is None:
            raise NotFoundError("Item not found.")
        return await self._react(
            session.profile_id, item.ref, item.title, item.entity_type, reaction, note, session.id
        )

    async def react_to_ref(
        self,
        owner_id: UUID,
        profile_id: UUID,
        item_ref: str,
        reaction: Reaction,
        note: str | None = None,
    ) -> FeedbackEffect:
        """The caregiver's reaction to an item by its ref, such as a card in Person mode."""
        profile = await self._profiles.get(owner_id, profile_id)
        found = await self._find(profile, item_ref)
        if found is None:
            raise NotFoundError("Item not found.")
        title, entity_type = found
        return await self._react(profile.id, item_ref, title, entity_type, reaction, note, None)

    async def person_signal(
        self,
        owner_id: UUID,
        profile_id: UUID,
        item_ref: str,
        signal: PersonSignal,
        played_s: int | None = None,
    ) -> FeedbackEffect:
        """A tap in Person mode. Only items on the shelf can get signals."""
        profile = await self._profiles.get(owner_id, profile_id)
        card = next(
            (card for card in await self._shelf.items_for(profile) if card.ref == item_ref), None
        )
        if card is None:
            raise InvalidInputError("Only items on the Person-mode shelf can get signals.")
        return await self.record_person_signal(profile.id, card, signal, played_s)

    async def record_person_signal(
        self, profile_id: UUID, card: ShelfItem, signal: PersonSignal, played_s: int | None
    ) -> FeedbackEffect:
        """Store a signal for a card the caller already checked is on the shelf."""
        if signal is PersonSignal.SKIPPED and not skip_counts(played_s):
            return FeedbackEffect(False, "Not counted: it played for 15 seconds or more.")
        now = self._clock()
        earlier = await self._feedback.list_for_profile(profile_id)
        if counted_today(earlier, card.ref, signal, now):
            return FeedbackEffect(False, "Already counted today.")
        await self._feedback.add(
            Feedback(
                profile_id=profile_id,
                item_ref=card.ref,
                title=card.title,
                actor=Actor.PERSON,
                kind=signal.value,
                entity_type=_entity_type(card),
                played_s=played_s,
                created_at=now,
            )
        )
        return FeedbackEffect(True, _SIGNAL_EFFECTS[signal])

    async def _react(
        self,
        profile_id: UUID,
        item_ref: str,
        title: str,
        entity_type: EntityType | None,
        reaction: Reaction,
        note: str | None,
        session_id: UUID | None,
    ) -> FeedbackEffect:
        await self._feedback.add(
            Feedback(
                profile_id=profile_id,
                item_ref=item_ref,
                title=title,
                actor=Actor.CAREGIVER,
                kind=reaction.value,
                entity_type=entity_type,
                session_id=session_id,
                note=_clean_note(note),
                created_at=self._clock(),
            )
        )
        if reaction is Reaction.REJECTED:
            await self._exclusions.block(profile_id, item_ref, title, ExclusionKind.REJECTED)
        elif reaction is Reaction.UPSET:
            await self._exclusions.block(profile_id, item_ref, title, ExclusionKind.HIDDEN)
        return FeedbackEffect(True, _REACTION_EFFECTS[reaction])

    async def _find(self, profile: Profile, item_ref: str) -> tuple[str, EntityType | None] | None:
        """The title and type behind a ref: a favourite, or an item of any session."""
        for favourite in profile.favourites:
            if favourite_ref(favourite) == item_ref:
                return favourite.song_title or favourite.name, search_type_for(favourite.kind)
        for session in await self._session_store.list_for_profile(profile.id):
            for item in session.items:
                if item.ref == item_ref:
                    return item.title, item.entity_type
        return None


def _clean_note(note: str | None) -> str | None:
    text = " ".join((note or "").split())[:NOTE_MAX]
    return text or None


def _entity_type(card: ShelfItem) -> EntityType | None:
    """The Qloo type behind a card. A song card has none: Qloo has no songs."""
    try:
        return EntityType(card.kind.value)
    except ValueError:
        return None
