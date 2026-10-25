"""Journal routes: entries, link suggestions and voice notes, nested under their profile.

Every route is scoped to the signed-in owner; someone else's profile or entry is a 404.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import CurrentUserDep, JournalServiceDep
from app.api.v1.schemas.journal import (
    JournalEntryCreate,
    JournalEntryOut,
    JournalEntryUpdate,
    JournalLinkOut,
    LinkDecision,
    TranscriptOut,
)
from app.application.services.journal import AUDIO_MAX_BYTES
from app.core.errors import InvalidInputError
from app.domain.journal import LinkStatus

router = APIRouter(prefix="/profiles/{profile_id}/journal", tags=["journal"])


@router.get("")
async def list_entries(
    profile_id: UUID,
    user: CurrentUserDep,
    journal: JournalServiceDep,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[JournalEntryOut]:
    """Entries newest first (by default the last 60 days)."""
    views = await journal.entries(user.id, profile_id, date_from, date_to)
    return [JournalEntryOut.from_view(view) for view in views]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entry(
    profile_id: UUID, body: JournalEntryCreate, user: CurrentUserDep, journal: JournalServiceDep
) -> JournalEntryOut:
    """Save an entry. The agent starts suggesting links: poll `link_run_id`."""
    view = await journal.create(user.id, profile_id, body.text, body.date, body.mood)
    return JournalEntryOut.from_view(view)


@router.post("/transcribe")
async def transcribe(
    profile_id: UUID,
    request: Request,
    user: CurrentUserDep,
    journal: JournalServiceDep,
    content_type: Annotated[str, Header()] = "",
) -> TranscriptOut:
    """Turn a voice note (the raw webm, ogg, mp4 or wav body) into text. The audio is
    discarded once transcribed."""
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > AUDIO_MAX_BYTES:
            raise InvalidInputError("Keep recordings under 2 minutes (10 MB).")
    text = await journal.transcribe(user.id, profile_id, bytes(audio), content_type)
    return TranscriptOut(text=text)


@router.patch("/links/{link_id}")
async def decide_link(
    profile_id: UUID,
    link_id: UUID,
    body: LinkDecision,
    user: CurrentUserDep,
    journal: JournalServiceDep,
) -> JournalLinkOut:
    """Confirm or reject one suggestion. A 409 when it's already decided."""
    view = await journal.decide(user.id, profile_id, link_id, LinkStatus(body.status))
    return JournalLinkOut.from_view(view)


@router.get("/{entry_id}")
async def get_entry(
    profile_id: UUID, entry_id: UUID, user: CurrentUserDep, journal: JournalServiceDep
) -> JournalEntryOut:
    """One entry with its links and suggestions."""
    return JournalEntryOut.from_view(await journal.get(user.id, profile_id, entry_id))


@router.patch("/{entry_id}")
async def update_entry(
    profile_id: UUID,
    entry_id: UUID,
    body: JournalEntryUpdate,
    user: CurrentUserDep,
    journal: JournalServiceDep,
) -> JournalEntryOut:
    """Change an entry. New text starts a new link run; confirmed links stay."""
    view = await journal.update(
        user.id,
        profile_id,
        entry_id,
        text=body.text,
        entry_date=body.date,
        mood=body.mood,
        mood_set="mood" in body.model_fields_set,
    )
    return JournalEntryOut.from_view(view)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    profile_id: UUID, entry_id: UUID, user: CurrentUserDep, journal: JournalServiceDep
) -> None:
    """Delete an entry, its links and the signals that came only from them."""
    await journal.delete(user.id, profile_id, entry_id)


@router.post("/{entry_id}/links/confirm-all")
async def confirm_all(
    profile_id: UUID, entry_id: UUID, user: CurrentUserDep, journal: JournalServiceDep
) -> JournalEntryOut:
    """Confirm every open suggestion on the entry."""
    return JournalEntryOut.from_view(await journal.confirm_all(user.id, profile_id, entry_id))


@router.post("/{entry_id}/links/suggest", status_code=status.HTTP_202_ACCEPTED)
async def suggest_links(
    profile_id: UUID, entry_id: UUID, user: CurrentUserDep, journal: JournalServiceDep
) -> JournalEntryOut:
    """Ask the agent for suggestions again, such as after a failed run."""
    return JournalEntryOut.from_view(await journal.suggest(user.id, profile_id, entry_id))
