"""link_journal step 2, `resolve` (code): the hint ladder for each media mention, sharing one
budget of `LINK_MAX_SEARCHES`. Only names reach Qloo, never the entry; a song is found through
its singer."""

from app.application.agent.ladder import Hints, Proposal, climb, ladder_context
from app.application.agent.resolve_state import LinkDeps, LinkState, Mention
from app.application.agent.tools.context import TYPE_NOUNS
from app.domain.journal import NodeKind
from app.domain.models import FavouriteKind

NODE = "resolve"


def hints_for(mention: Mention) -> Hints:
    """Ladder hints for one mention. A song's own title is kept but never searched."""
    if mention.kind == NodeKind.SONG.value:
        return Hints(
            kind=FavouriteKind.SONG,
            song_title=mention.text,
            singer=mention.artist,
            film=mention.film,
            year=mention.year,
        )
    if mention.kind == NodeKind.ARTIST.value:
        return Hints(kind=FavouriteKind.ARTIST, singer=mention.text)
    return Hints(kind=FavouriteKind(mention.kind), title=mention.text, year=mention.year)


async def resolve_mentions(state: LinkState, deps: LinkDeps) -> LinkState:
    """Each media mention with its best Qloo match, or None. Items already in the journal with a
    Qloo ID need no search."""
    media = [m for m in state.get("mentions", []) if m.kind != NodeKind.PLACE.value]
    songs = tuple(m.text for m in media if m.kind == NodeKind.SONG.value)
    ctx = ladder_context(
        deps.taste,
        deps.log,
        deps.profile_id,
        deps.blocklist,
        deps.max_searches,
        NODE,
        song_titles=songs,
    )
    known = await deps.journal.list_nodes(deps.profile_id)
    resolved: list[tuple[Mention, Proposal | None]] = []
    for mention in media:
        kind = NodeKind(mention.kind)
        if any(node.qloo_id and node.same_item(kind, mention.text, None) for node in known):
            await deps.log.info(NODE, f"Your journal mentioned {mention.text} → already there ✓.")
            resolved.append((mention, None))
            continue
        if ctx.budget_used:
            await deps.log.warn(NODE, f"Out of searches, so skipped {mention.text}.")
            continue
        proposals = await climb(ctx, hints_for(mention))
        wanted = FavouriteKind(mention.kind)
        match = next((p for p in proposals if p.kind is wanted), None)
        if match is None:
            await deps.log.info(NODE, f"Your journal mentioned {mention.text} → not in Qloo ✗.")
        else:
            noun = "song" if kind is NodeKind.SONG else TYPE_NOUNS[match.type]
            await deps.log.info(NODE, f"Your journal mentioned {mention.text} → found ({noun}) ✓.")
        resolved.append((mention, match))
    return {"resolved": resolved}
