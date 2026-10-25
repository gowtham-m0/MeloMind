"""resolve_favourite steps 2–9, `climb` (code): the hint ladder, within the search budget. With
no match, the run asks the user for a hint and offers to keep the favourite as text."""

from app.application.agent.ladder import Hints, climb, ladder_context
from app.application.agent.resolve_state import ResolveDeps, ResolveState
from app.domain.models import FavouriteKind

NODE = "ladder"


async def climb_ladder(state: ResolveState, deps: ResolveDeps) -> ResolveState:
    """Up to 3 proposals, or a question for the user."""
    hints = state["hints"]
    ctx = ladder_context(
        deps.taste,
        deps.log,
        deps.profile_id,
        deps.blocklist,
        deps.max_searches,
        NODE,
        song_titles=(hints.song_title,) if hints.song_title else (),
    )
    proposals = await climb(ctx, hints)
    if proposals:
        count = len(proposals)
        noun = "match" if count == 1 else "matches"
        await deps.log.info(NODE, f"Found {count} {noun} for you to choose from ✓.")
        return {"proposals": proposals, "question": None, "text_favourite": None}
    question = question_for(hints)
    await deps.log.info(NODE, f"No sure match in Qloo yet. Asked you: “{question}”")
    return {"proposals": [], "question": question, "text_favourite": text_favourite(hints)}


def question_for(hints: Hints) -> str:
    """What to ask the user, given what's still missing."""
    if hints.kind is FavouriteKind.SONG or hints.song_title:
        if not hints.singer:
            return "Who sings it, or which film is it from?"
        return "Which film is it from, or roughly what year?"
    if hints.kind in (FavouriteKind.MOVIE, FavouriteKind.TV_SHOW, FavouriteKind.BOOK):
        return "Can you add the year, or check the spelling?"
    return "Can you add a hint: the singer, the film or the year?"


def text_favourite(hints: Hints) -> dict[str, str | None] | None:
    """What "keep it as text" would save: the names worked out, never what was typed (a lyric
    is never stored). None when nothing name-like is known."""
    kind = hints.kind
    if kind is FavouriteKind.SONG or (kind is None and hints.song_title):
        name = hints.singer or hints.song_title
        if not name:
            return None
        return {"name": name, "kind": FavouriteKind.SONG.value, "song_title": hints.song_title}
    name = hints.title or hints.singer
    if not name:
        return None
    return {"name": name, "kind": (kind or FavouriteKind.ARTIST).value, "song_title": None}
