"""The resolver's `interpret` step (hint ladder rung 1): what did the user mean?

The LLM sees only what the user typed for this favourite, and its answer is checked in code:
any field that looks like a lyric or a sentence is dropped, so only names reach Qloo.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.application.agent.ladder import Hints
from app.domain.models import FavouriteKind
from app.domain.names import normalise_name

NAME_WORDS_MAX = 8
NAME_CHARS_MAX = 100
# Typed text this long is a lyric or a description, not a name: it's never searched as typed.
PLAIN_NAME_WORDS_MAX = 6
_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

INTERPRET_SYSTEM = (
    "You help someone add a favourite to a music, film, TV and book app. They typed a name, a "
    "song title, a line of a song they remember, or a description. Work out what they mean.\n"
    "Rules:\n"
    "- Fill only fields you are fairly sure of; use null otherwise.\n"
    "- title: the artist, film, TV show or book when they name one. Never a song.\n"
    "- song_title: the song, when they mean a song or quote one.\n"
    "- singer / composer / film / actor: for a song, who sings it, who composed it, the film it "
    "comes from and that film's lead actor.\n"
    '- tag: a genre or region when that is all you can tell, such as "Tamil film music".\n'
    "- They may write in English, Hindi, Tamil, Telugu, Malayalam, Punjabi or mixed (Hinglish), in "
    "Roman or native script. A lyric in Roman script, such as a Hindi or Tamil line, is "
    "common: recognise the song from it. Give singer, composer, film, actor and title in "
    "English letters, spelt the way a film or music database would.\n"
    "- Never repeat the lyric or the description in any field. Names only.\n"
    "- Never include anyone's personal details."
)


class Interpretation(BaseModel):
    """The model's guess at what the user meant."""

    kind: Literal["artist", "song", "movie", "tv_show", "book"] | None = None
    title: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    song_title: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    singer: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    composer: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    film: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    actor: str | None = Field(default=None, max_length=NAME_CHARS_MAX)
    year: int | None = Field(default=None, ge=1900, le=2030)
    tag: str | None = Field(default=None, max_length=60)


def interpret_prompt(text: str, kind: FavouriteKind | None, hint: str | None) -> str:
    """What the user typed, the kind they picked, and any hint they added."""
    lines = [f"They typed: {text}"]
    if kind is not None:
        lines.append(f"They are adding a {kind.value.replace('_', ' ')}.")
    if hint:
        lines.append(f"Their extra hint (singer, film or year): {hint}")
    return "\n".join(lines)


def _name_like(value: str | None, typed: str) -> str | None:
    """The value when it looks like a name: short, and not the long text the user typed."""
    if value is None:
        return None
    name = " ".join(value.split())
    if not name or len(name) > NAME_CHARS_MAX or len(name.split()) > NAME_WORDS_MAX:
        return None
    if len(typed.split()) > PLAIN_NAME_WORDS_MAX and normalise_name(name) == normalise_name(typed):
        return None
    return name


def hints_from(answer: Interpretation, text: str, kind: FavouriteKind | None) -> Hints:
    """The model's answer as ladder hints, keeping only name-like fields. The kind the user
    picked wins over the model's guess."""
    guessed = FavouriteKind(answer.kind) if answer.kind else None
    chosen = kind or guessed
    if chosen is FavouriteKind.SONG and answer.title and not answer.song_title:
        answer = answer.model_copy(update={"song_title": answer.title, "title": None})
    return Hints(
        kind=chosen,
        title=_name_like(answer.title, text) if chosen is not FavouriteKind.SONG else None,
        song_title=_name_like(answer.song_title, text),
        singer=_name_like(_lead(answer.singer), text),
        composer=_name_like(_lead(answer.composer), text),
        film=_name_like(answer.film, text),
        actor=_name_like(_lead(answer.actor), text),
        year=answer.year,
        tag=_name_like(answer.tag, text),
    )


_CREDITS = re.compile(r"\s*(?:,|;|\bfeat\.|\bfeat\b|\bft\.|\bft\b)\s*", re.IGNORECASE)


def _lead(names: str | None) -> str | None:
    """The first of several credited people ("A. R. Rahman, Javed Ali" → "A. R. Rahman"), since
    one Qloo search for all of them finds none."""
    if not names:
        return names
    return next((part for part in _CREDITS.split(names) if part.strip()), None)


def template_hints(text: str, kind: FavouriteKind | None, hint: str | None) -> Hints:
    """Hints without the LLM. Short text is taken as a name; long text may be a lyric, so it's
    never searched. A song's own title is never searched either: only the hint, as its singer."""
    words = len(text.split())
    year_match = _YEAR.search(hint or "")
    year = int(year_match.group(1)) if year_match else None
    extra = _name_like(_YEAR.sub("", hint or "").strip(" ,.-") or None, text)
    if kind is FavouriteKind.SONG:
        title = text if words <= PLAIN_NAME_WORDS_MAX else None
        return Hints(kind=kind, song_title=title, singer=extra, year=year)
    title = text if words <= PLAIN_NAME_WORDS_MAX else None
    if extra and kind in (None, FavouriteKind.ARTIST):
        return Hints(kind=kind, title=title, singer=extra, year=year)
    return Hints(kind=kind, title=title, film=extra, year=year)
