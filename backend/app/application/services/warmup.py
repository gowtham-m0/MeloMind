"""The Person-mode "this or that" warm-up: two cards at a time from the approved warm-up set.

The first pair differs in type or decade. After each tap, the next pair is the unseen item most
like the chosen one (Qloo scores the set), plus one different item to keep exploring. The card
that wasn't chosen gets no signal: not choosing isn't disliking.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.ports import EntityMatch, ExclusionRepository, SessionRepository
from app.application.services.feedback import FeedbackService
from app.application.services.profiles import ProfileService
from app.application.services.taste import TasteService
from app.core.errors import ConflictError, InvalidInputError
from app.domain.feedback import Blocklist, PersonSignal
from app.domain.sessions import (
    ItemSource,
    Session,
    SessionItem,
    SessionStatus,
    ShelfItem,
    ShelfOrigin,
)


@dataclass(frozen=True)
class WarmupStep:
    """The next two cards, or `done` when the warm-up is over."""

    pair: tuple[ShelfItem, ShelfItem] | None
    done: bool


DONE = WarmupStep(pair=None, done=True)


def _decade(item: SessionItem) -> int | None:
    return None if item.release_year is None else item.release_year // 10 * 10


def _different(anchor: SessionItem, others: Sequence[SessionItem]) -> SessionItem:
    """Another type if there is one, else another decade, else the next item."""
    return next(
        (item for item in others if item.entity_type is not anchor.entity_type),
        next((item for item in others if _decade(item) != _decade(anchor)), others[0]),
    )


def _as_match(item: SessionItem) -> EntityMatch:
    return EntityMatch(
        entity_id=item.ref,
        name=item.title,
        type=item.entity_type,
        source="demo_fixture" if item.source is ItemSource.DEMO_FIXTURE else "qloo_live",
        release_year=item.release_year,
    )


def _card(item: SessionItem) -> ShelfItem:
    card = ShelfItem.from_item(item, ShelfOrigin.WARMUP)
    if card is None:
        raise ValueError("Warm-up items always have media")
    return card


class WarmupService:
    """Pairs for the warm-up. Each choice is stored as a `chose` signal."""

    def __init__(
        self,
        profiles: ProfileService,
        sessions: SessionRepository,
        exclusions: ExclusionRepository,
        taste: TasteService,
        feedback: FeedbackService,
        pairs: int,
    ) -> None:
        self._profiles = profiles
        self._sessions = sessions
        self._exclusions = exclusions
        self._taste = taste
        self._feedback = feedback
        self._pairs = pairs

    async def next(
        self,
        owner_id: UUID,
        profile_id: UUID,
        chosen_ref: str | None,
        shown_refs: Sequence[str],
    ) -> WarmupStep:
        """Record the choice, if any, and return the next pair or `done`."""
        profile = await self._profiles.get(owner_id, profile_id)
        warmup = await self._approved_set(profile.id)
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        pool = [
            item
            for item in warmup.items
            if item.playable and not blocklist.blocks(item.ref, item.title)
        ]
        by_ref = {item.ref: item for item in pool}
        chosen: SessionItem | None = None
        if chosen_ref is not None:
            if chosen_ref not in {item.ref for item in warmup.items}:
                raise InvalidInputError("That item isn't in the warm-up set.")
            chosen = by_ref.get(chosen_ref)
            if chosen is not None:
                await self._feedback.record_person_signal(
                    profile.id, _card(chosen), PersonSignal.CHOSE, None
                )
        seen = set(shown_refs) | ({chosen_ref} if chosen_ref else set())
        pairs_done = len(set(shown_refs)) // 2
        unseen = [item for item in pool if item.ref not in seen]
        if pairs_done >= self._pairs or len(unseen) < 2:
            return DONE
        if chosen is None:
            first = unseen[0]
        else:
            ranked = await self._taste.score([_as_match(i) for i in unseen], _as_match(chosen))
            first = by_ref[ranked[0].entity_id]
        second = _different(first, [item for item in unseen if item is not first])
        # Alternate sides, so the similar card isn't always on the left.
        pair = (first, second) if pairs_done % 2 == 0 else (second, first)
        return WarmupStep(pair=(_card(pair[0]), _card(pair[1])), done=False)

    async def _approved_set(self, profile_id: UUID) -> Session:
        sessions = await self._sessions.list_for_profile(
            profile_id, frozenset({SessionStatus.APPROVED})
        )
        warmup = next((session for session in sessions if session.is_warmup), None)
        if warmup is None:
            raise ConflictError("The warm-up set isn't approved yet.")
        return warmup
