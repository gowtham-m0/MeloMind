"""The research agent's system prompt and task, built from the brief (docs/AGENT.md §10).

The agent sees only the first name, country and the titles of favourites and liked items: never
journal text or keys.
"""

from collections.abc import Callable

from app.application.agent.tools.context import TYPE_NOUNS
from app.application.agent.types import FeedContext, ResearchBrief

FEATURED = 12

_TIER_GUIDANCE = {
    "A": "Use the signals below: Qloo expands them well. Mix them across calls.",
    "B": (
        "Only one or two signals are known. Use them in every call, and add a genre tag from "
        "find_tags if a type comes back thin."
    ),
    "C": (
        "Nothing specific is known yet. For films, TV and books, ask for popular picks with a "
        "popularity_min of 0.7 (and the country for films and TV). For artists, first get "
        "films, then use the best few films as the signal: never ask for artists without one."
    ),
}


def research_system_prompt(
    brief: ResearchBrief,
    context: FeedContext,
    max_qloo_calls: int,
    alias: Callable[[str], str] = str,
) -> str:
    """The system prompt: role, brief, allowed signals (by their short ids) and rules."""
    lines = [
        "You research music, films, TV shows and books for a personal home feed, like a "
        "streaming app's home screen but across all four.",
        "",
        f"User: {context.first_name}.",
        f"Goal: {brief.goal}",
        f"Aim for about {brief.per_type} of each type: artists, films, TV shows and books.",
    ]
    if brief.country_code:
        lines.append(f"Country (films and TV only): {brief.country_code}.")
    if brief.popularity_min is not None:
        lines.append(f"Popularity floor: {brief.popularity_min}.")
    lines += ["", _TIER_GUIDANCE[brief.tier]]
    if brief.signals:
        lines += ["", "Signals you may use, strongest and newest first (id: name):"]
        lines += [
            f"- {alias(signal.ref)}: {signal.name}"
            + (f" ({TYPE_NOUNS[signal.entity_type]})" if signal.entity_type else " (tag)")
            for signal in brief.signals
        ]
    if context.song_titles:
        lines += [
            "",
            "Favourite songs (never search these titles; Qloo has no songs): "
            + ", ".join(f"“{title}”" for title in context.song_titles)
            + ".",
        ]
    if brief.tag_hints:
        lines.append(f"Genres they've been into lately: {', '.join(brief.tag_hints)}.")
    lines += [
        "",
        "Steps:",
        "1. In your first reply, call get_insights once for EACH of the four types, all in the "
        "same reply (parallel calls). Use the first few signals above in signal_ids, and spread "
        "the others across types so the feed isn't about one thing.",
        "2. Only if a type came back with too few, call get_insights for it once more, looser.",
        f"3. Then call submit_candidates once with your {FEATURED} best picks to lead the "
        "feed, at least two of each type. A why is optional (at most 8 words). Every other "
        "result is kept too, so don't list them. That ends your work.",
        "",
        "Rules:",
        "- Submit only ids that get_insights returned: picks are Qloo's recommendations, "
        "never your own ideas.",
        "- Use only ids from this brief or your tool results. Don't search for the signals above.",
        "- search_entities and find_tags are only for finding extra signals. Never search a "
        "song title or a lyric.",
        f"- You have {max_qloo_calls} Qloo calls in total.",
    ]
    return "\n".join(lines)


def research_task(brief: ResearchBrief) -> str:
    """The first message: start researching."""
    return (
        f"Research about {brief.per_type} artists, films, TV shows and books, then submit your "
        f"{FEATURED} best picks."
    )
