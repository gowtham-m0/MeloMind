"""resolve_favourite step 1, `interpret` (LLM, with a template fallback): what did the user
mean? The answer is checked in code, so only names go on to the ladder."""

import asyncio
import logging

from app.application.agent.ladder import Hints
from app.application.agent.prompts.interpret import (
    INTERPRET_SYSTEM,
    Interpretation,
    hints_from,
    interpret_prompt,
    template_hints,
)
from app.application.agent.resolve_state import ResolveDeps, ResolveState
from app.domain.models import FavouriteKind

logger = logging.getLogger(__name__)

NODE = "interpret"
INTERPRET_TIMEOUT_SECONDS = 15.0

_NOUNS = {
    FavouriteKind.ARTIST: "an artist",
    FavouriteKind.SONG: "a song",
    FavouriteKind.MOVIE: "a film",
    FavouriteKind.TV_SHOW: "a TV show",
    FavouriteKind.BOOK: "a book",
}


async def interpret(state: ResolveState, deps: ResolveDeps) -> ResolveState:
    """Turn the typed text (and any hint) into ladder hints."""
    text = state["text"]
    kind = state.get("kind")
    hint = state.get("hint")
    hints: Hints | None = None
    if deps.language_model is not None:
        try:
            answer = await asyncio.wait_for(
                deps.language_model.structured(
                    INTERPRET_SYSTEM, interpret_prompt(text, kind, hint), Interpretation
                ),
                INTERPRET_TIMEOUT_SECONDS,
            )
            hints = hints_from(answer, text, kind)
        except Exception as exc:
            logger.warning("Interpret failed: %s", type(exc).__name__)
            await deps.log.info(NODE, "The AI didn't answer, so read it as typed.")
    if hints is None:
        hints = template_hints(text, kind, hint)
    await deps.log.info(NODE, describe(hints, lyric=len(text.split()) > 6))
    return {"hints": hints}


def describe(hints: Hints, lyric: bool) -> str:
    """The interpretation in plain words: names only, never the lyric or the song title."""
    what = _NOUNS.get(hints.kind, "something") if hints.kind else "something"
    parts = [f"Interpreted {'a lyric hint' if lyric else 'your hint'} as {what}"]
    if hints.title:
        parts.append(f"named {hints.title}")
    if hints.singer:
        parts.append(f"sung by {hints.singer}")
    if hints.composer:
        parts.append(f"composed by {hints.composer}")
    if hints.film:
        parts.append(f"from the film {hints.film}")
    if hints.year:
        parts.append(f"from around {hints.year}")
    return ", ".join(parts) + "."
