"""link_journal step 1, `extract` (LLM through Groq only, with a rule-based fallback): what the
entry mentions. The entry's text is never logged, and never sent to Qloo (rule 11)."""

import asyncio
import logging
from collections import Counter
from collections.abc import Iterable

from app.application.agent.prompts.extract import (
    CONFIDENCE_MIN,
    EXTRACT_SYSTEM,
    ExtractOutput,
    extract_prompt,
)
from app.application.agent.resolve_state import LinkDeps, LinkState, Mention
from app.domain.names import mentioned_in, normalise_name

logger = logging.getLogger(__name__)

NODE = "extract"
EXTRACT_TIMEOUT_SECONDS = 15.0
NAME_WORDS_MAX = 8
KNOWN_NAME_MIN = 3

_NOUNS = {
    "artist": ("an artist", "artists"),
    "song": ("a song", "songs"),
    "movie": ("a film", "films"),
    "tv_show": ("a TV show", "TV shows"),
    "book": ("a book", "books"),
    "place": ("a place", "places"),
}


async def extract_mentions(state: LinkState, deps: LinkDeps) -> LinkState:
    """The entry's mentions, checked against its text."""
    text = state["entry"].body or ""
    mentions: list[Mention] | None = None
    if deps.language_model is not None:
        try:
            answer = await asyncio.wait_for(
                deps.language_model.structured(EXTRACT_SYSTEM, extract_prompt(text), ExtractOutput),
                EXTRACT_TIMEOUT_SECONDS,
            )
            mentions = checked(answer, text)
        except Exception as exc:
            logger.warning("Extract failed: %s", type(exc).__name__)
            await deps.log.warn(
                NODE, "Couldn't read your entry with the AI just now; looked for things you love."
            )
    else:
        await deps.log.info(NODE, "No AI reader is set up, so looked for things you love.")
    ai_read = mentions is not None
    if mentions is None:
        mentions = known_mentions(text, deps.known_names)
    await deps.log.info(NODE, describe(mentions))
    return {"mentions": mentions, "ai_read": ai_read}


def checked(answer: ExtractOutput, text: str) -> list[Mention]:
    """The model's mentions that are sure enough, name-like and really in the text, once each."""
    found: dict[tuple[str, str], Mention] = {}
    for raw in answer.mentions:
        name = " ".join(raw.text.split())
        if raw.confidence < CONFIDENCE_MIN or not name or len(name.split()) > NAME_WORDS_MAX:
            continue
        if not mentioned_in(name, text):
            continue
        found.setdefault(
            (raw.kind, normalise_name(name)),
            Mention(
                kind=raw.kind,
                text=name,
                artist=_name_like(raw.artist),
                film=_name_like(raw.film),
                year=raw.year,
            ),
        )
    return list(found.values())


def known_mentions(text: str, known: Iterable[tuple[str, str]]) -> list[Mention]:
    """Without the AI: the names of things the user already loves or wrote about, where the
    entry mentions them. Nothing leaves the server for this."""
    found: dict[tuple[str, str], Mention] = {}
    for kind, name in known:
        if len(normalise_name(name)) < KNOWN_NAME_MIN or not mentioned_in(name, text):
            continue
        found.setdefault((kind, normalise_name(name)), Mention(kind=kind, text=name))
    return list(found.values())


def describe(mentions: list[Mention]) -> str:
    """A count by kind, never the text: "Read your entry: found a film and an artist."."""
    if not mentions:
        return "Read your entry: found nothing to link."
    counts = Counter(mention.kind for mention in mentions)
    parts = [
        _NOUNS[kind][0] if count == 1 else f"{count} {_NOUNS[kind][1]}"
        for kind, count in counts.items()
    ]
    listing = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Read your entry: found {listing}."


def _name_like(value: str | None) -> str | None:
    if value is None:
        return None
    name = " ".join(value.split())
    return name if name and len(name.split()) <= NAME_WORDS_MAX else None
