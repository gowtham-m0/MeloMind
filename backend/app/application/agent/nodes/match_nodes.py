"""link_journal step 3, `match` (code): each mention against the journal's existing items and
places, through `find_journal_links`. Anything rejected before for this entry is skipped."""

from app.application.agent.ladder import Proposal
from app.application.agent.resolve_state import LinkDeps, LinkState, LinkTarget, Mention
from app.application.agent.tools.journal_links import find_journal_links
from app.domain.journal import JournalNode, LinkStatus, NodeKind

NODE = "match"

_REASONS = {
    NodeKind.ARTIST: "You mentioned this artist.",
    NodeKind.MOVIE: "You mentioned this film.",
    NodeKind.TV_SHOW: "You mentioned this show.",
    NodeKind.BOOK: "You mentioned this book.",
    NodeKind.PLACE: "You mentioned this place.",
}


def reason_for(kind: NodeKind, creator: str | None, known: bool) -> str:
    """A short reason for the suggestion."""
    if known:
        return "You've written about it before."
    if kind is NodeKind.SONG:
        return f"You mentioned this song by {creator}." if creator else "You mentioned this song."
    return _REASONS[kind]


async def match_nodes(state: LinkState, deps: LinkDeps) -> LinkState:
    """Where each suggestion points: an existing node, or a new one."""
    entry = state["entry"]
    places: list[tuple[Mention, Proposal | None]] = [
        (m, None) for m in state.get("mentions", []) if m.kind == NodeKind.PLACE.value
    ]
    targets: list[LinkTarget] = []
    for mention, proposal in [*state.get("resolved", []), *places]:
        target = await _target(deps, entry, mention, proposal)
        if target is not None:
            targets.append(target)
    return {"targets": targets}


async def _target(
    deps: LinkDeps, entry: JournalNode, mention: Mention, proposal: Proposal | None
) -> LinkTarget | None:
    kind = NodeKind(mention.kind)
    keeps_own_title = kind in (NodeKind.SONG, NodeKind.PLACE)
    title = mention.text if keeps_own_title or proposal is None else proposal.name
    qloo_id = proposal.entity_id if proposal else None
    matches = await find_journal_links(
        deps.journal, deps.log, deps.profile_id, NODE, title, kind, qloo_id
    )
    existing = next((m for m in matches if m.node.same_item(kind, title, qloo_id)), None)
    if existing is not None:
        status = existing.status_from(entry.id)
        if status is LinkStatus.REJECTED:
            await deps.log.info(NODE, f"Skipped {title}: you said no to it before.")
            return None
        if status is not None:
            return None
        return LinkTarget(mention, existing.node, False, reason_for(kind, None, known=True))
    if proposal is None and kind is not NodeKind.PLACE:
        return None
    creator = proposal.name if proposal and kind is NodeKind.SONG else None
    node = JournalNode(
        profile_id=deps.profile_id,
        kind=kind,
        title=title,
        year=proposal.year if proposal and kind is not NodeKind.SONG else None,
        qloo_id=qloo_id,
        creator=creator,
        image_url=proposal.image_url if proposal else None,
    )
    return LinkTarget(mention, node, True, reason_for(kind, creator, known=False))
