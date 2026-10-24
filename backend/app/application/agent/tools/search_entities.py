"""`search_entities`: names to Qloo entities, over `TasteGraph.search`."""

from app.application.agent.tools.context import TYPE_NOUNS, ToolContext, ToolRefusalError
from app.application.agent.types import Candidate
from app.core.errors import UpstreamError
from app.domain.models import EntityType
from app.domain.names import names_match

SEARCH_TAKE = 5
NAME_MAX = 100
SONG_TITLE_REFUSAL = (
    "That is a song title, and Qloo has no songs. Search the singer, the composer or the film "
    "the song comes from instead."
)


async def search_entities(
    ctx: ToolContext, name: str, entity_type: EntityType | None = None
) -> list[Candidate]:
    """Up to 5 matches for a name. Refuses song titles, which Qloo can't know (rule 12)."""
    text = " ".join(name.split())
    if not text or len(text) > NAME_MAX:
        raise ToolRefusalError(f"Give a name of 1 to {NAME_MAX} characters.")
    label = f"{TYPE_NOUNS[entity_type]} {text}" if entity_type else text
    if any(names_match(text, title) for title in ctx.context.song_titles):
        await ctx.log.info(ctx.node, "Didn't search a song title: Qloo has no songs.")
        raise ToolRefusalError(SONG_TITLE_REFUSAL)
    await ctx.spend_qloo_call()
    types = (entity_type,) if entity_type else ()
    try:
        matches = await ctx.taste.search(text, types, SEARCH_TAKE)
    except UpstreamError:
        await ctx.log.warn(ctx.node, f"Searched {label} → Qloo didn't answer.")
        raise ToolRefusalError("Qloo didn't answer. Try a different query.") from None
    found = [
        Candidate(
            entity_id=match.entity_id,
            name=match.name,
            entity_type=match.type,
            source=ctx.source,
            signal=f"found by searching for {text}",
            release_year=match.release_year,
            popularity=match.popularity,
            image_url=match.image_url,
            description=match.description,
            isbn13=match.isbn13,
            tags=match.tags,
            external=tuple(sorted(match.external.items())),
        )
        for match in matches
        if not ctx.context.blocklist.blocks(match.entity_id, match.name)
    ]
    for candidate in found:
        ctx.remember(candidate)
    outcome = f"{len(found)} found ✓" if found else "no match ✗"
    await ctx.log.info(ctx.node, f"Searched {label} → {outcome}.")
    return found
