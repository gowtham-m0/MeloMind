"""The research agent's system prompt and task, built from the mode's brief (docs/AGENT.md §10).

The agent sees only the first name, birth year, places and favourites: never notes or keys.
"""

from app.application.agent.tools.context import TYPE_NOUNS, count_noun
from app.application.agent.types import PlanContext, ResearchBrief

# Submit a few more than the session needs, so the guardrails have spares to swap in.
EXTRA_PICKS = 4

_TIER_GUIDANCE = {
    "A": "Use the favourites as signals: Qloo expands them well.",
    "B": (
        "There are only one or two favourites. Use them, plus the older-audience signal and "
        "any region or decade tags you find."
    ),
    "C": (
        "Nothing specific is known yet. For films, TV and books, use the older-audience signal, "
        "the era years and a high popularity floor: the big hits of their youth. For artists, "
        "first find era films, then use those films (and any era or region tags) as signals. "
        "Never ask for artists with the age signal alone: it returns today's bands."
    ),
}


def _mix_text(brief: ResearchBrief) -> str:
    return ", ".join(count_noun(count, entity_type) for entity_type, count in brief.mix)


def research_system_prompt(brief: ResearchBrief, context: PlanContext, max_qloo_calls: int) -> str:
    """The system prompt: role, brief, allowed signals and rules."""
    start, end = brief.era
    lines = [
        "You research songs, films, TV and books for a caregiver-led music and memory session. "
        "The caregiver approves everything before the person sees it.",
        "",
        f"Person: {context.first_name}, born {context.birth_year}.",
    ]
    if context.places:
        lines.append(f"Places they lived: {', '.join(context.places)}.")
    if context.languages:
        lines.append(f"Languages: {', '.join(context.languages)}.")
    lines += [
        "",
        f"Goal: {brief.goal}",
        f"Mix needed: {_mix_text(brief)}, plus {brief.spares} spares.",
        f"Era: {start}–{end}, the years they were 13 to 21. Use year_min and year_max for "
        "films, TV and books. Artists have no year filter, so steer them with era signals.",
    ]
    if brief.country_code:
        lines.append(f"Country (films and TV only): {brief.country_code}.")
    if brief.popularity_min is not None:
        lines.append(f"Popularity floor: {brief.popularity_min}.")
    lines += ["", _TIER_GUIDANCE[brief.tier]]
    if brief.signals:
        lines += ["", "Signals you may use (ID: name):"]
        lines += [
            f"- {signal.ref}: {signal.name}"
            + (f" ({TYPE_NOUNS[signal.entity_type]})" if signal.entity_type else " (tag)")
            for signal in brief.signals
        ]
    if context.song_titles:
        lines += [
            "",
            "Favourite songs (never search these titles; search the singer instead): "
            + ", ".join(f"“{title}”" for title in context.song_titles)
            + ".",
        ]
    if brief.tag_hints:
        lines.append(f"Tags worth looking up: {', '.join(brief.tag_hints)}.")
    want = brief.item_count + brief.spares + EXTRA_PICKS
    lines += [
        "",
        "Steps:",
        "1. In your first reply, call get_insights once for EACH type in the mix, all in the "
        "same reply (parallel calls), using the signal IDs above.",
        "2. Only if a type came back with too few, call get_insights for it once more, looser.",
        f"3. Then call submit_candidates once with about {want} of the best results, covering "
        "every type in the mix. A why is optional (at most 8 words). That ends your work.",
        "",
        "Rules:",
        "- Submit only entity IDs that get_insights returned: candidates are Qloo's "
        "recommendations, never your own ideas.",
        "- Use only IDs from this brief or your tool results. The favourites' IDs are above: "
        "don't search for them.",
        "- search_entities and find_tags are only for finding extra signals. Never search a "
        "song title or a lyric: Qloo has no songs.",
        f"- You have {max_qloo_calls} Qloo calls in total. No health claims.",
    ]
    return "\n".join(lines)


def research_task(brief: ResearchBrief) -> str:
    """The first message: start researching."""
    return (
        f"Research candidates for this mix: {_mix_text(brief)}, plus {brief.spares} spares. "
        "When you have enough, call submit_candidates."
    )
