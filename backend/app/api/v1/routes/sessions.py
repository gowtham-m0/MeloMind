"""Session routes: plan, review, approve, play and react. Others' sessions are 404."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, FeedbackServiceDep, SessionServiceDep
from app.api.v1.schemas.sessions import (
    FeedbackOut,
    ItemsPatch,
    PlanRequestIn,
    ReactionIn,
    SessionDraftOut,
    SessionSummaryOut,
)

router = APIRouter(tags=["sessions"])


@router.post("/profiles/{profile_id}/sessions/plan", status_code=status.HTTP_202_ACCEPTED)
async def plan_session(
    profile_id: UUID, body: PlanRequestIn, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """Start planning. Returns at once with status `planning`; poll the agent run's log."""
    session = await sessions.plan(user.id, profile_id, body.mode, body.target_minutes)
    return SessionDraftOut.from_domain(session)


@router.get("/profiles/{profile_id}/history")
async def get_history(
    profile_id: UUID, user: CurrentUserDep, sessions: SessionServiceDep
) -> list[SessionSummaryOut]:
    """The profile's sessions and warm-up sets, newest first."""
    return [
        SessionSummaryOut.from_domain(session)
        for session in await sessions.history(user.id, profile_id)
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """One session with its items."""
    return SessionDraftOut.from_domain(await sessions.get(user.id, session_id))


@router.patch("/sessions/{session_id}/items")
async def edit_items(
    session_id: UUID, body: ItemsPatch, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """Remove, reorder or change the prompts of a draft's items."""
    session = await sessions.edit_items(
        user.id, session_id, order=body.order, removed=body.removed, prompts=body.prompts
    )
    return SessionDraftOut.from_domain(session)


@router.post("/sessions/{session_id}/approve")
async def approve_session(
    session_id: UUID, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """Approve a draft. `409` unless it's a draft."""
    return SessionDraftOut.from_domain(await sessions.approve(user.id, session_id))


@router.post("/sessions/{session_id}/start")
async def start_session(
    session_id: UUID, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """Start an approved session. A warm-up set can't be started."""
    return SessionDraftOut.from_domain(await sessions.start(user.id, session_id))


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: UUID, user: CurrentUserDep, sessions: SessionServiceDep
) -> SessionDraftOut:
    """Finish a session in progress."""
    return SessionDraftOut.from_domain(await sessions.complete(user.id, session_id))


@router.post("/sessions/{session_id}/items/{item_id}/feedback")
async def react_to_item(
    session_id: UUID,
    item_id: UUID,
    body: ReactionIn,
    user: CurrentUserDep,
    feedback: FeedbackServiceDep,
) -> FeedbackOut:
    """The caregiver's reaction. `rejected` excludes the item; `upset` hides it for review."""
    effect = await feedback.react_to_item(user.id, session_id, item_id, body.reaction, body.note)
    return FeedbackOut.from_effect(effect)
