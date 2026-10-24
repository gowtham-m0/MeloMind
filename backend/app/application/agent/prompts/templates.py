"""Template text: used when the LLM is off, fails, times out or writes something we won't show."""

from collections.abc import Sequence

NEW_TAGS_MAX = 2


def template_summary(
    item_count: int,
    new_count: int,
    tags: Sequence[str],
    previous_tags: Sequence[str],
    first_feed: bool,
) -> str:
    """What changed since the last feed, in one line."""
    if first_feed:
        return f"Your feed is ready: {item_count} picks across music, films, TV and books."
    fresh = [tag for tag in tags if tag not in previous_tags][:NEW_TAGS_MAX]
    lead = f"{new_count} new picks" if new_count else "Your picks are reshuffled"
    if fresh:
        return f"{lead}, with more {' and '.join(fresh).lower()} since last time."
    return f"{lead}, tuned to what you've been enjoying."
