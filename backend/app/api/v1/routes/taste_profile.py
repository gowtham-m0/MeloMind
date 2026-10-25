"""Taste page routes and the favourite resolver, nested under their profile."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUserDep,
    FeedbackServiceDep,
    ResolveServiceDep,
    TasteProfileServiceDep,
)
from app.api.v1.schemas.journal import ResolveIn, ResolveOut, TasteMapOut, TasteOut

router = APIRouter(prefix="/profiles/{profile_id}", tags=["taste"])


@router.get("/taste")
async def get_taste(
    profile_id: UUID,
    user: CurrentUserDep,
    taste: TasteProfileServiceDep,
    feedback: FeedbackServiceDep,
) -> TasteOut:
    """Your taste in a sentence, top tags, counts by type, favourites and recent likes."""
    summary = await taste.taste(user.id, profile_id)
    return TasteOut.from_summary(summary, await feedback.states(profile_id))


@router.get("/taste/map")
async def get_taste_map(
    profile_id: UUID, user: CurrentUserDep, taste: TasteProfileServiceDep
) -> TasteMapOut:
    """The taste map: confirmed links only, capped, most connected first."""
    return TasteMapOut.from_map(await taste.taste_map(user.id, profile_id))


@router.post("/favourites/resolve", status_code=status.HTTP_202_ACCEPTED)
async def resolve_favourite(
    profile_id: UUID, body: ResolveIn, user: CurrentUserDep, resolve: ResolveServiceDep
) -> ResolveOut:
    """Start looking up what the user typed. Poll the run for up to 3 proposals, or a
    `needs_hint` question. The text is never stored."""
    run_id = await resolve.start(user.id, profile_id, body.text, body.kind, body.hint)
    return ResolveOut(agent_run_id=run_id)
