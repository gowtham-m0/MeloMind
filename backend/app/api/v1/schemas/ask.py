"""Schemas for asking the agent for a row and for taste match."""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.api.v1.schemas.feed import FeedRowOut, Ref
from app.application.agent.taste_match import MatchResult

Mood = Literal["chill", "happy", "focused", "melancholy", "energetic"]


class AskIn(BaseModel):
    """What to ask for: words, a mood or a surprise (at least one). A surprise wins over a mood,
    and a mood over words. The words are used for this run only."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    mood: Mood | None = None
    kind: Literal["surprise"] | None = None


class AskOut(BaseModel):
    """The run to poll. When it's done, its `result` is the row."""

    agent_run_id: UUID


class TasteMatchIn(BaseModel):
    """Another of your profiles, or a friend's favourites (Qloo entity IDs from search)."""

    other_profile_id: UUID | None = None
    favourites: list[Ref] | None = Field(default=None, max_length=5)


class TasteMatchOut(BaseModel):
    """What two tastes share, a 0 to 1 score and the "For you both" row."""

    shared_tags: list[str]
    score: float
    row: FeedRowOut

    @classmethod
    def from_result(cls, result: MatchResult) -> Self:
        """Build from the service result."""
        return cls(
            shared_tags=list(result.shared_tags),
            score=result.score,
            row=FeedRowOut.from_domain(result.row, {}),
        )
