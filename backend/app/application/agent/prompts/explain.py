"""The `explain` step's prompt: one friendly line on what changed in the feed.

The LLM sees only titles, tag names and counts: never journal text, keys or other personal data.
"""

from collections.abc import Sequence

from pydantic import BaseModel, Field

SUMMARY_MAX = 140

EXPLAIN_SYSTEM = (
    "You write one short, friendly line for the top of a personal recommendation feed, saying "
    "what changed since last time. Plain words, no hype, no emoji, no exclamation marks, no "
    "numbers or lists of tags. Mention only the titles and tags you are given. At most 20 words.\n"
    "Examples:\n"
    "- More indie rock and sci-fi today, because you liked Foster the People.\n"
    "- A fresh mix today, still close to the thrillers you've been enjoying."
)


class ExplainOutput(BaseModel):
    """The model's answer."""

    summary: str = Field(description="One line, at most 20 words.")


def explain_prompt(
    liked: Sequence[str],
    tags: Sequence[str],
    previous_tags: Sequence[str],
    new_count: int,
    item_count: int,
    first_feed: bool,
) -> str:
    """The facts the line may use."""
    lines = [
        f"First feed: {'yes' if first_feed else 'no'}.",
        f"Picks in the feed: {item_count}. New since last time: {new_count}.",
        f"Top tags now: {', '.join(tags) or 'none'}.",
        f"Top tags last time: {', '.join(previous_tags) or 'none'}.",
        f"Recently liked: {', '.join(liked) or 'nothing yet'}.",
    ]
    return "\n".join(lines)
