"""Ask the agent for a row, and taste match, nested under their profile."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AskServiceDep, CurrentUserDep, TasteMatchServiceDep
from app.api.v1.schemas.ask import AskIn, AskOut, TasteMatchIn, TasteMatchOut

router = APIRouter(prefix="/profiles/{profile_id}", tags=["ask"])


@router.post("/ask", status_code=status.HTTP_202_ACCEPTED)
async def ask(profile_id: UUID, body: AskIn, user: CurrentUserDep, asks: AskServiceDep) -> AskOut:
    """Start building one extra row: for a mood, a surprise or the user's words. Poll the run:
    its `result` is the row. Counts toward the same hourly limit as feed builds."""
    run_id = await asks.start(user.id, profile_id, body.text, body.mood, body.kind)
    return AskOut(agent_run_id=run_id)


@router.post("/taste-match")
async def taste_match(
    profile_id: UUID, body: TasteMatchIn, user: CurrentUserDep, matches: TasteMatchServiceDep
) -> TasteMatchOut:
    """Compare this taste with another of your profiles, or with a friend's favourites."""
    result = await matches.match(user.id, profile_id, body.other_profile_id, body.favourites)
    return TasteMatchOut.from_result(result)
