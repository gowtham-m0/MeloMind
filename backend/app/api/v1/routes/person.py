"""Person-mode routes: the shelf, the warm-up, the person's taps and the caregiver's reactions
from inside Person mode. Nothing here returns a reason or a prompt."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, FeedbackServiceDep, ShelfServiceDep, WarmupServiceDep
from app.api.v1.schemas.person import (
    PersonSignalIn,
    RefReactionIn,
    ShelfItemOut,
    WarmupNextIn,
    WarmupNextOut,
)
from app.api.v1.schemas.sessions import FeedbackOut

router = APIRouter(prefix="/profiles/{profile_id}", tags=["person mode"])


@router.get("/shelf")
async def get_shelf(
    profile_id: UUID, user: CurrentUserDep, shelf: ShelfServiceDep
) -> list[ShelfItemOut]:
    """Approved, playable cards only. Excluded and hidden items never appear."""
    return [ShelfItemOut.from_domain(card) for card in await shelf.items(user.id, profile_id)]


@router.post("/warmup/next")
async def next_warmup_pair(
    profile_id: UUID, body: WarmupNextIn, user: CurrentUserDep, warmup: WarmupServiceDep
) -> WarmupNextOut:
    """Record the choice and return the next pair. `409` without an approved warm-up set."""
    step = await warmup.next(user.id, profile_id, body.chosen_ref, body.shown_refs)
    return WarmupNextOut.from_step(step)


@router.post("/person-signals")
async def add_person_signal(
    profile_id: UUID, body: PersonSignalIn, user: CurrentUserDep, feedback: FeedbackServiceDep
) -> FeedbackOut:
    """A tap in Person mode, for an item on the shelf."""
    effect = await feedback.person_signal(
        user.id, profile_id, body.item_ref, body.signal, body.played_s
    )
    return FeedbackOut.from_effect(effect)


@router.post("/reactions")
async def react_to_ref(
    profile_id: UUID, body: RefReactionIn, user: CurrentUserDep, feedback: FeedbackServiceDep
) -> FeedbackOut:
    """The caregiver's reaction to a card, from the Person-mode caregiver button."""
    effect = await feedback.react_to_ref(
        user.id, profile_id, body.item_ref, body.reaction, body.note
    )
    return FeedbackOut.from_effect(effect)
