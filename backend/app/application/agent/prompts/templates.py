"""Template reasons and prompts: used when the LLM is off, fails, times out or writes something
we won't show. Prompts are open and gentle, never memory tests (rule 10)."""

from app.application.agent.types import PlanContext
from app.domain.models import EntityType
from app.domain.sessions import ItemSource, SessionItem

_PROMPTS: dict[EntityType, tuple[str, ...]] = {
    EntityType.ARTIST: (
        "What does this music bring to mind?",
        "How does this song make you feel?",
        "Shall we sing along together?",
    ),
    EntityType.MOVIE: (
        "What do you like about this film?",
        "What does this scene make you think of?",
    ),
    EntityType.TV_SHOW: (
        "What do you enjoy about shows like this?",
        "What does this theme tune bring to mind?",
    ),
    EntityType.BOOK: (
        "What do you enjoy in a good story?",
        "What kind of stories do you like best?",
    ),
}
_NOUNS: dict[EntityType, str] = {
    EntityType.ARTIST: "music",
    EntityType.MOVIE: "film",
    EntityType.TV_SHOW: "show",
    EntityType.BOOK: "book",
}


def template_reason(item: SessionItem, context: PlanContext) -> str:
    """Why the item was picked, from the signal that led to it."""
    if item.source is ItemSource.FAVOURITE:
        return f"One of {context.first_name}'s favourites."
    basis = item.signal.strip()
    if not basis:
        return f"A well-loved {_NOUNS[item.entity_type]} from {context.first_name}'s youth."
    return f"{basis[0].upper()}{basis[1:]}."


def template_prompt(item: SessionItem) -> str:
    """An open, gentle conversation starter for the caregiver."""
    options = _PROMPTS[item.entity_type]
    return options[item.position % len(options)]
