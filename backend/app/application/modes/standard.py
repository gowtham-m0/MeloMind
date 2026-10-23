"""`standard`: a session of about 20 minutes, with conversation prompts."""

from app.application.agent.types import PlanContext
from app.application.modes.base import MixMode
from app.domain.models import EntityType


class StandardMode(MixMode):
    """4 artists, 2 films, 1 TV show and 1 book, plus 4 spares, fitted to the target length."""

    name = "standard"
    mix = (
        (EntityType.ARTIST, 4),
        (EntityType.MOVIE, 2),
        (EntityType.TV_SHOW, 1),
        (EntityType.BOOK, 1),
    )
    spares = 4
    min_candidates = 8

    def goal(self, context: PlanContext) -> str:
        """A session they're likely to love."""
        return (
            f"A {context.target_minutes}-minute session of music, films, TV and a book that "
            f"{context.first_name} is likely to love."
        )
