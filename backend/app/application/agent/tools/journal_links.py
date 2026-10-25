"""`find_journal_links` and `propose_links`: thin wrappers over the journal repository, always
scoped to one profile, with every call logged."""

from dataclasses import dataclass
from uuid import UUID

from app.application.agent.log import RunLog
from app.application.ports import JournalRepository
from app.domain.journal import (
    JournalLink,
    JournalNode,
    LinkKind,
    LinkSource,
    LinkStatus,
    NodeKind,
)
from app.domain.names import normalise_name

QUERY_MAX = 200
REASON_MAX = 200


@dataclass(frozen=True)
class NodeMatch:
    """An existing node and every link to it, rejected ones included, so a rejected suggestion
    is recognised and never made again."""

    node: JournalNode
    links: tuple[JournalLink, ...]

    def status_from(self, entry_id: UUID, kind: LinkKind = LinkKind.MENTIONS) -> LinkStatus | None:
        """The status of this entry's link to the node, if it has one."""
        return next(
            (link.status for link in self.links if link.from_id == entry_id and link.kind is kind),
            None,
        )


async def find_journal_links(
    journal: JournalRepository,
    log: RunLog,
    profile_id: UUID,
    node: str,
    query: str,
    kind: NodeKind | None = None,
    qloo_id: str | None = None,
) -> list[NodeMatch]:
    """Existing items and places in this profile's journal with this name (or Qloo ID)."""
    text = " ".join(query.split())[:QUERY_MAX]
    if not text:
        return []
    kinds = frozenset({kind}) if kind else None
    nodes = [
        candidate
        for candidate in await journal.list_nodes(profile_id, kinds)
        if candidate.kind is not NodeKind.ENTRY
        and (
            candidate.same_item(candidate.kind, text, qloo_id)
            or normalise_name(candidate.title) == normalise_name(text)
        )
    ]
    links = await journal.list_links(profile_id) if nodes else []
    matches = [
        NodeMatch(node=found, links=tuple(link for link in links if link.to_id == found.id))
        for found in nodes
    ]
    outcome = f"{len(matches)} found ✓" if matches else "not there yet"
    await log.info(node, f"Looked in your journal for {text} → {outcome}.")
    return matches


@dataclass(frozen=True)
class LinkProposal:
    """One suggestion: a link from the entry to an existing node or a new one."""

    target: JournalNode
    is_new: bool
    reason: str


async def propose_links(
    journal: JournalRepository,
    log: RunLog,
    profile_id: UUID,
    node: str,
    entry_id: UUID,
    proposals: list[LinkProposal],
) -> int:
    """Save the suggestions as `suggested` links from the agent. A link that already exists,
    whatever its status, is never made again, so a rejected one stays rejected. The number
    saved."""
    existing = {
        (link.from_id, link.to_id, link.kind)
        for link in await journal.list_links(profile_id)
        if link.from_id == entry_id
    }
    saved = 0
    for proposal in proposals:
        target = proposal.target
        if target.profile_id != profile_id or target.kind is NodeKind.ENTRY:
            continue
        if not target.title.strip() or (entry_id, target.id, LinkKind.MENTIONS) in existing:
            continue
        if proposal.is_new:
            await journal.add_node(target)
        await journal.add_link(
            JournalLink(
                profile_id=profile_id,
                from_id=entry_id,
                to_id=target.id,
                kind=LinkKind.MENTIONS,
                source=LinkSource.AGENT,
                status=LinkStatus.SUGGESTED,
                reason=proposal.reason[:REASON_MAX],
            )
        )
        existing.add((entry_id, target.id, LinkKind.MENTIONS))
        saved += 1
    noun = "suggestion" if saved == 1 else "suggestions"
    await log.info(node, f"Saved {saved} {noun} for you to confirm.")
    return saved
