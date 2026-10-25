"""`JournalRepository` in memory: for tests, and for local runs without `DATABASE_URL`."""

from copy import deepcopy
from datetime import date
from uuid import UUID

from app.domain.journal import JournalLink, JournalNode, NodeKind


class InMemoryJournalRepository:
    """Nodes and links in dicts, copied in and out so callers can't change stored data."""

    def __init__(self) -> None:
        self._nodes: dict[UUID, JournalNode] = {}
        self._links: dict[UUID, JournalLink] = {}

    async def add_node(self, node: JournalNode) -> None:
        """Store a new node."""
        self._nodes[node.id] = deepcopy(node)

    async def update_node(self, node: JournalNode) -> None:
        """Save a node's fields."""
        if node.id in self._nodes:
            self._nodes[node.id] = deepcopy(node)

    async def get_node(self, profile_id: UUID, node_id: UUID) -> JournalNode | None:
        """One node of this profile."""
        node = self._nodes.get(node_id)
        return deepcopy(node) if node and node.profile_id == profile_id else None

    async def list_nodes(
        self, profile_id: UUID, kinds: frozenset[NodeKind] | None = None
    ) -> list[JournalNode]:
        """The profile's nodes, oldest first."""
        owned = [
            node
            for node in self._nodes.values()
            if node.profile_id == profile_id and (kinds is None or node.kind in kinds)
        ]
        return [deepcopy(node) for node in sorted(owned, key=lambda node: node.created_at)]

    async def list_entries(
        self, profile_id: UUID, date_from: date | None = None, date_to: date | None = None
    ) -> list[JournalNode]:
        """Entries between two dates, newest first."""
        entries = [
            node
            for node in await self.list_nodes(profile_id, frozenset({NodeKind.ENTRY}))
            if node.date is not None
            and (date_from is None or node.date >= date_from)
            and (date_to is None or node.date <= date_to)
        ]
        return sorted(entries, key=lambda node: (node.date, node.created_at), reverse=True)

    async def delete_node(self, profile_id: UUID, node_id: UUID) -> bool:
        """Delete a node and its links."""
        node = self._nodes.get(node_id)
        if node is None or node.profile_id != profile_id:
            return False
        del self._nodes[node_id]
        self._links = {
            link_id: link
            for link_id, link in self._links.items()
            if node_id not in (link.from_id, link.to_id)
        }
        return True

    async def add_link(self, link: JournalLink) -> None:
        """Store a new link, at most one per `(from_id, to_id, kind)`."""
        if any(
            (known.from_id, known.to_id, known.kind) == (link.from_id, link.to_id, link.kind)
            for known in self._links.values()
        ):
            raise ValueError("That link already exists.")
        self._links[link.id] = deepcopy(link)

    async def update_link(self, link: JournalLink) -> None:
        """Save a link's status and reason."""
        if link.id in self._links:
            self._links[link.id] = deepcopy(link)

    async def get_link(self, profile_id: UUID, link_id: UUID) -> JournalLink | None:
        """One link of this profile."""
        link = self._links.get(link_id)
        return deepcopy(link) if link and link.profile_id == profile_id else None

    async def list_links(self, profile_id: UUID) -> list[JournalLink]:
        """Every link of the profile, oldest first."""
        owned = [link for link in self._links.values() if link.profile_id == profile_id]
        return [deepcopy(link) for link in sorted(owned, key=lambda link: link.created_at)]

    async def delete_for_profile(self, profile_id: UUID) -> None:
        """Delete the profile's whole journal."""
        self._nodes = {k: v for k, v in self._nodes.items() if v.profile_id != profile_id}
        self._links = {k: v for k, v in self._links.items() if v.profile_id != profile_id}
