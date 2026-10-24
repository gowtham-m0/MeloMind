"""Feed routes: the latest feed, refreshing it, item details, feedback, the library and the quiz.

Every route is scoped to the signed-in owner; someone else's profile is a 404.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUserDep,
    FeedbackServiceDep,
    FeedServiceDep,
    ItemServiceDep,
    LibraryServiceDep,
    QuizServiceDep,
)
from app.api.v1.schemas.feed import (
    FeedbackIn,
    FeedbackOut,
    FeedOut,
    ItemDetailOut,
    LibraryOut,
    PreviewOut,
    QuizIn,
    QuizStepOut,
)
from app.application.services.feedback import ItemRef
from app.domain.feedback import Signal

router = APIRouter(prefix="/profiles/{profile_id}", tags=["feed"])


@router.get("/feed")
async def get_feed(
    profile_id: UUID, user: CurrentUserDep, feeds: FeedServiceDep, feedback: FeedbackServiceDep
) -> FeedOut:
    """The newest finished feed. A 404 means there's none yet: start one with refresh."""
    feed = await feeds.latest(user.id, profile_id)
    return FeedOut.from_domain(feed, await feedback.states(profile_id))


@router.post("/feed/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_feed(profile_id: UUID, user: CurrentUserDep, feeds: FeedServiceDep) -> FeedOut:
    """Start building a new feed in the background. Poll its agent run, then get the feed."""
    return FeedOut.from_domain(await feeds.refresh(user.id, profile_id), {})


@router.get("/items/{ref}")
async def get_item(
    profile_id: UUID,
    ref: str,
    user: CurrentUserDep,
    items: ItemServiceDep,
    feedback: FeedbackServiceDep,
) -> ItemDetailOut:
    """An item with more like it. Excluded items are a 404."""
    detail = await items.detail(user.id, profile_id, ref)
    return ItemDetailOut.from_detail(detail, await feedback.states(profile_id))


@router.post("/items/{ref}/preview")
async def preview_item(
    profile_id: UUID, ref: str, user: CurrentUserDep, items: ItemServiceDep
) -> PreviewOut:
    """Look up a YouTube preview now. A 404 means none: hide the button."""
    return PreviewOut.from_media(await items.preview(user.id, profile_id, ref))


@router.post("/feedback")
async def send_feedback(
    profile_id: UUID, body: FeedbackIn, user: CurrentUserDep, feedback: FeedbackServiceDep
) -> FeedbackOut:
    """Like, save, open, dislike or dismiss an item."""
    effect = await feedback.record(
        user.id,
        profile_id,
        ItemRef(ref=body.ref, title=body.title, entity_type=body.entity_type),
        Signal(body.signal),
        body.platform,
    )
    return FeedbackOut.from_effect(effect)


@router.get("/library")
async def get_library(
    profile_id: UUID,
    user: CurrentUserDep,
    library: LibraryServiceDep,
    feedback: FeedbackServiceDep,
) -> LibraryOut:
    """Liked and saved items, newest first."""
    result = await library.library(user.id, profile_id)
    return LibraryOut.from_library(result, await feedback.states(profile_id))


@router.post("/quiz/next")
async def quiz_next(
    profile_id: UUID,
    body: QuizIn,
    user: CurrentUserDep,
    quiz: QuizServiceDep,
) -> QuizStepOut:
    """Record the pick, if any, and get the next pair of the taste quiz."""
    step = await quiz.next(user.id, profile_id, body.picked_ref, body.shown_refs)
    return QuizStepOut.from_step(step)
