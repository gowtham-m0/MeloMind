"""Use cases for the journal: entries, the agent's link suggestions, confirming them, and voice.

Entries are private to their profile (rule 11). Saving or changing an entry's text starts a
`link` run in the background. Only confirmed links count: confirming a media item with a Qloo
ID adds a `journal_confirmed` signal and marks the feed stale; deleting the entry takes the
signal away again when nothing else confirms that item.
"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from functools import partial
from typing import Protocol
from uuid import UUID

from app.application.agent.runners import LinkOutcome
from app.application.ports import (
    AgentRunRepository,
    ExclusionRepository,
    FeedbackRepository,
    JournalRepository,
    SpeechToText,
)
from app.application.services.background import BackgroundRunner
from app.application.services.feed import FeedService
from app.application.services.feedback import FeedbackService, ItemRef
from app.application.services.profiles import ProfileService
from app.core.errors import ConflictError, InvalidInputError, NotFoundError, UpstreamError
from app.domain.feedback import Blocklist, Signal
from app.domain.journal import (
    ENTRY_TEXT_MAX,
    MEDIA_KINDS,
    MOOD_MAX,
    JournalLink,
    JournalNode,
    LinkStatus,
    NodeKind,
    signal_type,
)
from app.domain.models import FavouriteKind, Profile, utc_now
from app.domain.runs import AgentRun, AgentStep, RunKind, RunStatus, StepLevel

logger = logging.getLogger(__name__)

DEFAULT_DAYS = 60
LINK_TIMEOUT_SECONDS = 60.0
AUDIO_MAX_BYTES = 10 * 1024 * 1024
AUDIO_MAX_SECONDS = 120.0
AUDIO_TYPES = frozenset(
    {"audio/webm", "audio/ogg", "audio/mp4", "audio/wav", "audio/x-wav", "audio/wave"}
)
AUDIO_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
}
NODE = "link"


class JournalLinker(Protocol):
    """Suggests links for an entry (the agent's link_journal workflow)."""

    async def link(
        self,
        run_id: UUID,
        entry: JournalNode,
        blocklist: Blocklist,
        known_names: Sequence[tuple[str, str]],
    ) -> LinkOutcome:
        """Save suggestions for the entry."""
        ...


@dataclass(frozen=True)
class LinkView:
    """A link with the node it points to."""

    link: JournalLink
    target: JournalNode


@dataclass(frozen=True)
class EntryView:
    """An entry with its confirmed links and its open suggestions (never the rejected ones).
    `link_run_id` is set when a link run was just started."""

    entry: JournalNode
    links: list[LinkView]
    suggestions: list[LinkView]
    link_run_id: UUID | None = None


class JournalService:
    """The journal for its owner's profiles: someone else's is reported as not found."""

    def __init__(
        self,
        profiles: ProfileService,
        journal: JournalRepository,
        feedback: FeedbackRepository,
        feedback_service: FeedbackService,
        exclusions: ExclusionRepository,
        feeds: FeedService,
        runs: AgentRunRepository,
        linker: JournalLinker,
        runner: BackgroundRunner,
        speech: SpeechToText | None = None,
    ) -> None:
        self._profiles = profiles
        self._journal = journal
        self._feedback = feedback
        self._feedback_service = feedback_service
        self._exclusions = exclusions
        self._feeds = feeds
        self._runs = runs
        self._linker = linker
        self._runner = runner
        self._speech = speech

    async def entries(
        self,
        owner_id: UUID,
        profile_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[EntryView]:
        """Entries newest first, by default from the last 60 days."""
        profile = await self._profiles.get(owner_id, profile_id)
        if date_from is None and date_to is None:
            date_from = utc_now().date() - timedelta(days=DEFAULT_DAYS)
        entries = await self._journal.list_entries(profile.id, date_from, date_to)
        nodes, links = await self._graph(profile.id)
        return [_view(entry, nodes, links) for entry in entries]

    async def get(self, owner_id: UUID, profile_id: UUID, entry_id: UUID) -> EntryView:
        """One entry."""
        profile = await self._profiles.get(owner_id, profile_id)
        entry = await self._entry(profile.id, entry_id)
        nodes, links = await self._graph(profile.id)
        return _view(entry, nodes, links)

    async def create(
        self,
        owner_id: UUID,
        profile_id: UUID,
        text: str,
        entry_date: date | None = None,
        mood: str | None = None,
    ) -> EntryView:
        """Save a new entry and start suggesting links for it."""
        profile = await self._profiles.get(owner_id, profile_id)
        day = _check_date(entry_date) or utc_now().date()
        entry = JournalNode(
            profile_id=profile.id,
            kind=NodeKind.ENTRY,
            title=day.isoformat(),
            body=_clean_text(text),
            date=day,
            mood=_clean_mood(mood),
        )
        await self._journal.add_node(entry)
        run_id = await self._start_link_run(profile, entry)
        nodes, links = await self._graph(profile.id)
        return _view(entry, nodes, links, run_id)

    async def update(
        self,
        owner_id: UUID,
        profile_id: UUID,
        entry_id: UUID,
        *,
        text: str | None = None,
        entry_date: date | None = None,
        mood: str | None = None,
        mood_set: bool = False,
    ) -> EntryView:
        """Change an entry. New text starts a new link run; confirmed links stay."""
        profile = await self._profiles.get(owner_id, profile_id)
        entry = await self._entry(profile.id, entry_id)
        new_text = _clean_text(text) if text is not None else None
        text_changed = new_text is not None and new_text != entry.body
        if new_text is not None:
            entry.body = new_text
        if entry_date is not None:
            entry.date = _check_date(entry_date)
            entry.title = entry_date.isoformat()
        if mood_set:
            entry.mood = _clean_mood(mood)
        entry.updated_at = utc_now()
        await self._journal.update_node(entry)
        run_id = await self._start_link_run(profile, entry) if text_changed else None
        nodes, links = await self._graph(profile.id)
        return _view(entry, nodes, links, run_id)

    async def suggest(self, owner_id: UUID, profile_id: UUID, entry_id: UUID) -> EntryView:
        """Suggest links for an entry again (after a failed run, say)."""
        profile = await self._profiles.get(owner_id, profile_id)
        entry = await self._entry(profile.id, entry_id)
        run_id = await self._start_link_run(profile, entry)
        nodes, links = await self._graph(profile.id)
        return _view(entry, nodes, links, run_id)

    async def delete(self, owner_id: UUID, profile_id: UUID, entry_id: UUID) -> None:
        """Delete an entry and its links, and the signals that came only from them."""
        profile = await self._profiles.get(owner_id, profile_id)
        entry = await self._entry(profile.id, entry_id)
        nodes, links = await self._graph(profile.id)
        touched = {link.to_id for link in links if link.from_id == entry.id}
        await self._journal.delete_node(profile.id, entry.id)
        remaining = [link for link in links if entry.id not in (link.from_id, link.to_id)]
        changed = False
        for node_id in touched:
            node = nodes.get(node_id)
            if node is None:
                continue
            if not any(link.to_id == node_id for link in remaining):
                await self._journal.delete_node(profile.id, node_id)
            changed |= await self._drop_signal_if_unconfirmed(profile.id, node, nodes, remaining)
        if changed:
            await self._feeds.mark_stale(profile.id)

    async def decide(
        self, owner_id: UUID, profile_id: UUID, link_id: UUID, status: LinkStatus
    ) -> LinkView:
        """Confirm or reject one suggestion. Deciding twice is a conflict."""
        if status is LinkStatus.SUGGESTED:
            raise InvalidInputError("Confirm or reject the suggestion.")
        profile = await self._profiles.get(owner_id, profile_id)
        link = await self._journal.get_link(profile.id, link_id)
        if link is None:
            raise NotFoundError("Link not found.")
        if link.status is not LinkStatus.SUGGESTED:
            raise ConflictError("You've already decided on this one.")
        target = await self._journal.get_node(profile.id, link.to_id)
        if target is None:
            raise NotFoundError("Link not found.")
        await self._set_status(profile.id, link, target, status)
        return LinkView(link=link, target=target)

    async def confirm_all(self, owner_id: UUID, profile_id: UUID, entry_id: UUID) -> EntryView:
        """Confirm every open suggestion on an entry."""
        profile = await self._profiles.get(owner_id, profile_id)
        entry = await self._entry(profile.id, entry_id)
        nodes, links = await self._graph(profile.id)
        for link in links:
            target = nodes.get(link.to_id)
            if link.from_id == entry.id and link.status is LinkStatus.SUGGESTED and target:
                await self._set_status(profile.id, link, target, LinkStatus.CONFIRMED)
        nodes, links = await self._graph(profile.id)
        return _view(entry, nodes, links)

    async def transcribe(
        self, owner_id: UUID, profile_id: UUID, audio: bytes, content_type: str
    ) -> str:
        """The words in a voice note. The audio is only passed on, never stored or logged."""
        await self._profiles.get(owner_id, profile_id)
        media_type = content_type.split(";")[0].strip().lower()
        if media_type not in AUDIO_TYPES:
            raise InvalidInputError("Send a webm, ogg, mp4 or wav recording.")
        if not audio:
            raise InvalidInputError("The recording is empty.")
        if len(audio) > AUDIO_MAX_BYTES:
            raise InvalidInputError("Keep recordings under 2 minutes (10 MB).")
        if self._speech is None:
            raise UpstreamError("Voice notes aren't set up on the server. Type it instead.")
        filename = f"entry.{AUDIO_EXTENSIONS[media_type]}"
        transcript = await self._speech.transcribe(audio, filename, media_type)
        if transcript.duration_s is not None and transcript.duration_s > AUDIO_MAX_SECONDS + 5:
            raise InvalidInputError("Keep recordings under 2 minutes.")
        text = " ".join(transcript.text.split())
        if not text:
            raise UpstreamError("Couldn't hear that. Try again or type it.")
        return text[:ENTRY_TEXT_MAX]

    async def _set_status(
        self, profile_id: UUID, link: JournalLink, target: JournalNode, status: LinkStatus
    ) -> None:
        link.status = status
        await self._journal.update_link(link)
        if status is LinkStatus.CONFIRMED:
            await self._add_signal(profile_id, target)

    async def _add_signal(self, profile_id: UUID, target: JournalNode) -> None:
        """A `journal_confirmed` signal for a media item Qloo knows, once per item."""
        entity_type = signal_type(target.kind)
        if target.qloo_id is None or entity_type is None:
            return
        earlier = await self._feedback.list_for_profile(profile_id)
        if any(
            entry.item_ref == target.qloo_id and entry.kind is Signal.JOURNAL_CONFIRMED
            for entry in earlier
        ):
            return
        title = target.creator if target.kind is NodeKind.SONG and target.creator else target.title
        await self._feedback_service.record_for(
            profile_id,
            ItemRef(ref=target.qloo_id, title=title, entity_type=entity_type),
            Signal.JOURNAL_CONFIRMED,
        )

    async def _drop_signal_if_unconfirmed(
        self,
        profile_id: UUID,
        node: JournalNode,
        nodes: dict[UUID, JournalNode],
        remaining: list[JournalLink],
    ) -> bool:
        """Remove the item's journal signal when no confirmed link to it is left."""
        if node.qloo_id is None or node.kind not in MEDIA_KINDS:
            return False
        still_confirmed = any(
            link.status is LinkStatus.CONFIRMED
            and (other := nodes.get(link.to_id)) is not None
            and other.qloo_id == node.qloo_id
            for link in remaining
        )
        if still_confirmed:
            return False
        removed = await self._feedback.delete_signals(
            profile_id, node.qloo_id, Signal.JOURNAL_CONFIRMED
        )
        return removed > 0

    async def _start_link_run(self, profile: Profile, entry: JournalNode) -> UUID:
        run = AgentRun(profile_id=profile.id, kind=RunKind.LINK)
        await self._runs.add(run)
        await self._runner.spawn(partial(self._execute_link, run.id, profile, entry))
        return run.id

    async def _execute_link(self, run_id: UUID, profile: Profile, entry: JournalNode) -> None:
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        known = await self._known_names(profile)
        try:
            outcome = await asyncio.wait_for(
                self._linker.link(run_id, entry, blocklist, known), LINK_TIMEOUT_SECONDS
            )
        except Exception as exc:
            logger.warning("Linking a journal entry failed: %s", type(exc).__name__)
            await self._runs.append_step(
                run_id,
                AgentStep(
                    node=NODE,
                    message="Couldn't suggest links this time. Try again.",
                    level=StepLevel.WARNING,
                ),
            )
            await self._runs.finish(run_id, RunStatus.FAILED, {"entry_id": str(entry.id)})
            return
        await self._runs.finish(
            run_id,
            RunStatus.DONE,
            {"entry_id": str(entry.id), "suggested": outcome.suggested, "ai_read": outcome.ai_read},
        )

    async def _known_names(self, profile: Profile) -> list[tuple[str, str]]:
        """Names the rule-based fallback may spot: verified favourites and journal items."""
        names: list[tuple[str, str]] = []
        for favourite in profile.favourites:
            if not favourite.verified:
                continue
            if favourite.kind is FavouriteKind.SONG:
                names.append((NodeKind.ARTIST.value, favourite.name))
            else:
                names.append((favourite.kind.value, favourite.name))
        for node in await self._journal.list_nodes(profile.id, MEDIA_KINDS | {NodeKind.PLACE}):
            names.append((node.kind.value, node.title))
        return names

    async def _entry(self, profile_id: UUID, entry_id: UUID) -> JournalNode:
        entry = await self._journal.get_node(profile_id, entry_id)
        if entry is None or entry.kind is not NodeKind.ENTRY:
            raise NotFoundError("Journal entry not found.")
        return entry

    async def _graph(self, profile_id: UUID) -> tuple[dict[UUID, JournalNode], list[JournalLink]]:
        nodes = {node.id: node for node in await self._journal.list_nodes(profile_id)}
        return nodes, await self._journal.list_links(profile_id)


def _view(
    entry: JournalNode,
    nodes: dict[UUID, JournalNode],
    links: list[JournalLink],
    run_id: UUID | None = None,
) -> EntryView:
    own = [
        LinkView(link=link, target=nodes[link.to_id])
        for link in links
        if link.from_id == entry.id and link.to_id in nodes
    ]
    return EntryView(
        entry=entry,
        links=[view for view in own if view.link.status is LinkStatus.CONFIRMED],
        suggestions=[view for view in own if view.link.status is LinkStatus.SUGGESTED],
        link_run_id=run_id,
    )


def _clean_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise InvalidInputError("Write something first.")
    if len(text) > ENTRY_TEXT_MAX:
        raise InvalidInputError(f"Keep entries under {ENTRY_TEXT_MAX} characters.")
    return text


def _clean_mood(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    mood = " ".join(value.split()).lower()
    if len(mood) > MOOD_MAX:
        raise InvalidInputError(f"Keep the mood under {MOOD_MAX} characters.")
    return mood


def _check_date(value: date | None) -> date | None:
    if value is not None and value > utc_now().date() + timedelta(days=1):
        raise InvalidInputError("The entry's date can't be in the future.")
    return value
