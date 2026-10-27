"""link_journal step 1, `extract`: the artists, songs, films, TV shows, books and places an
entry mentions, and its mood. The model sees the one entry's text, through Groq only (rule 11).
Mentions are checked in code against the text, so nothing the model makes up gets through."""

from typing import Literal

from pydantic import BaseModel, Field

MENTIONS_MAX = 12
CONFIDENCE_MIN = 0.5

EXTRACT_SYSTEM = (
    "You read one private journal entry and list the music, films, TV shows, books and places "
    "it mentions by name.\n"
    "Rules:\n"
    "- kind is one of: artist, song, movie, tv_show, book, place.\n"
    "- The entry may be in English, Hindi, Tamil or another Indian language, or mixed (Hinglish), "
    "in Roman or native script.\n"
    "- text: the name exactly as written in the entry, in the script it was written in.\n"
    "- For a song, add its artist (and film) if the entry says so or it is well known.\n"
    "- Never list people the writer knows (family, friends, colleagues), even by name. Only "
    "public artists and titles.\n"
    "- Never list vague things such as 'a podcast' or 'some music'.\n"
    "- confidence: 0 to 1, how sure you are it is a real title of that kind.\n"
    "- mood: one word for the entry's mood, or null."
)


class ExtractedMention(BaseModel):
    """One mention the model found."""

    kind: Literal["artist", "song", "movie", "tv_show", "book", "place"]
    text: str = Field(max_length=100)
    artist: str | None = Field(default=None, max_length=100)
    film: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2030)
    confidence: float = Field(default=0.0, ge=0, le=1)


class ExtractOutput(BaseModel):
    """The model's answer."""

    mentions: list[ExtractedMention] = Field(default_factory=list, max_length=MENTIONS_MAX)
    mood: str | None = Field(default=None, max_length=30)


def extract_prompt(text: str) -> str:
    """The entry to read."""
    return f"Journal entry:\n{text}"
