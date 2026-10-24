"""Use cases for feedback: like, save, open, dislike and "not interested".

Every signal is stored for learning. `not_interested` also excludes the item and removes it from
the current feed at once (rule 3). `opened` counts once per item per day.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports import ExclusionRepository, FeedbackRepository
from app.application.services.feed import FeedService
from app.application.services.profiles import ProfileService
from app.core.errors import InvalidInputError
from app.domain.feedback import Exclusion, Feedback, Signal
from app.domain.models import EntityType, utc_now
from app.domain.policies import counted_today, item_states

REF_MAX = 120
TITLE_MAX = 200
PLATFORM_MAX = 32

# Signals the app records itself (the quiz, the journal), never sent by the client.
INTERNAL_SIGNALS = frozenset({Signal.QUIZ_PICK, Signal.JOURNAL_CONFIRMED})
# Signals that change what the next feed would show.
STALE_SIGNALS = frozenset(
    {
        Signal.LIKED,
        Signal.UNLIKED,
        Signal.SAVED,
        Signal.UNSAVED,
        Signal.DISLIKED,
        Signal.NOT_INTERESTED,
    }
)

_EFFECTS = {
    Signal.LIKED: "Liked. You'll see more like this.",
    Signal.UNLIKED: "Removed from your likes.",
    Signal.SAVED: "Saved for later.",
    Signal.UNSAVED: "Removed from saved.",
    Signal.OPENED: "Noted.",
    Signal.DISLIKED: "Got it. You'll see fewer like this.",
    Signal.NOT_INTERESTED: "Got it. It won't show up again.",
}


@dataclass(frozen=True)
class FeedbackEffect:
    """Whether the signal counted, what it changes in plain English, and whether the feed is
    now out of date."""

    counted: bool
    effect: str
    stale: bool


@dataclass(frozen=True)
class ItemRef:
    """The item a signal is about."""

    ref: str
    title: str
    entity_type: EntityType | None = None


class FeedbackService:
    """Stores signals for their owner's profiles."""

    def __init__(
        self,
        profiles: ProfileService,
        feedback: FeedbackRepository,
        exclusions: ExclusionRepository,
        feeds: FeedService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._profiles = profiles
        self._feedback = feedback
        self._exclusions = exclusions
        self._feeds = feeds
        self._clock = clock

    async def record(
        self,
        owner_id: UUID,
        profile_id: UUID,
        item: ItemRef,
        signal: Signal,
        platform: str | None = None,
    ) -> FeedbackEffect:
        """A signal the user gave. The quiz and journal signals can't be sent this way."""
        if signal in INTERNAL_SIGNALS:
            raise InvalidInputError("That signal is recorded by the app itself.")
        profile = await self._profiles.get(owner_id, profile_id)
        clean = ItemRef(
            ref=_clean(item.ref, REF_MAX, "The item ref"),
            title=_clean(item.title, TITLE_MAX, "The title"),
            entity_type=item.entity_type,
        )
        return await self.record_for(profile.id, clean, signal, _clean_platform(platform))

    async def record_for(
        self, profile_id: UUID, item: ItemRef, signal: Signal, platform: str | None = None
    ) -> FeedbackEffect:
        """Store a signal for a profile the caller already checked."""
        now = self._clock()
        if signal is Signal.OPENED:
            earlier = await self._feedback.list_for_profile(profile_id)
            if counted_today(earlier, item.ref, signal, now):
                return FeedbackEffect(False, "Already counted today.", False)
        await self._feedback.add(
            Feedback(
                profile_id=profile_id,
                item_ref=item.ref,
                title=item.title,
                kind=signal,
                entity_type=item.entity_type,
                platform=platform,
                created_at=now,
            )
        )
        if signal is Signal.NOT_INTERESTED:
            await self._exclude(profile_id, item)
        stale = signal in STALE_SIGNALS or signal in INTERNAL_SIGNALS
        if stale:
            stale = await self._feeds.mark_stale(profile_id)
        return FeedbackEffect(True, _EFFECTS.get(signal, "Noted."), stale)

    async def states(self, profile_id: UUID) -> dict[str, frozenset[Signal]]:
        """Which items are liked or saved, for the cards' heart and bookmark."""
        return item_states(await self._feedback.list_for_profile(profile_id))

    async def _exclude(self, profile_id: UUID, item: ItemRef) -> None:
        existing = await self._exclusions.list_for_profile(profile_id)
        if not any(entry.entity_ref == item.ref for entry in existing):
            await self._exclusions.save(
                Exclusion(
                    profile_id=profile_id,
                    entity_ref=item.ref,
                    title=item.title,
                    entity_type=item.entity_type,
                    created_at=self._clock(),
                )
            )
        await self._feeds.remove_item(profile_id, item.ref)


def _clean(value: str, max_length: int, label: str) -> str:
    text = " ".join(value.split())
    if not text or len(text) > max_length:
        raise InvalidInputError(f"{label} must be 1 to {max_length} characters.")
    return text


def _clean_platform(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    if not text or len(text) > PLATFORM_MAX or not text.replace("_", "").isalnum():
        raise InvalidInputError("Unknown platform.")
    return text
