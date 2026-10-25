"""`JournalRepository` on Postgres (`journal_nodes` and `journal_links`)."""

from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.journal import (
    JournalLink,
    JournalNode,
    LinkKind,
    LinkSource,
    LinkStatus,
    NodeKind,
)
from app.infrastructure.persistence.models import JournalLinkRow, JournalNodeRow


def _node_to_domain(row: JournalNodeRow) -> JournalNode:
    return JournalNode(
        id=row.id,
        profile_id=row.profile_id,
        kind=NodeKind(row.kind),
        title=row.title,
        body=row.body,
        date=row.entry_date,
        mood=row.mood,
        year=row.year,
        qloo_id=row.qloo_id,
        creator=row.creator,
        image_url=row.image_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _node_to_row(node: JournalNode) -> JournalNodeRow:
    return JournalNodeRow(
        id=node.id,
        profile_id=node.profile_id,
        kind=node.kind.value,
        title=node.title,
        body=node.body,
        entry_date=node.date,
        mood=node.mood,
        year=node.year,
        qloo_id=node.qloo_id,
        creator=node.creator,
        image_url=node.image_url,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _link_to_domain(row: JournalLinkRow) -> JournalLink:
    return JournalLink(
        id=row.id,
        profile_id=row.profile_id,
        from_id=row.from_id,
        to_id=row.to_id,
        kind=LinkKind(row.kind),
        source=LinkSource(row.source),
        status=LinkStatus(row.status),
        reason=row.reason,
        created_at=row.created_at,
    )


def _link_to_row(link: JournalLink) -> JournalLinkRow:
    return JournalLinkRow(
        id=link.id,
        profile_id=link.profile_id,
        from_id=link.from_id,
        to_id=link.to_id,
        kind=link.kind.value,
        source=link.source.value,
        status=link.status.value,
        reason=link.reason,
        created_at=link.created_at,
    )


class PostgresJournalRepository:
    """Journal nodes and links in Postgres. The database deletes links with their nodes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add_node(self, node: JournalNode) -> None:
        """Store a new node."""
        async with self._sessions() as db, db.begin():
            db.add(_node_to_row(node))

    async def update_node(self, node: JournalNode) -> None:
        """Save a node's fields."""
        async with self._sessions() as db, db.begin():
            await db.merge(_node_to_row(node))

    async def get_node(self, profile_id: UUID, node_id: UUID) -> JournalNode | None:
        """One node of this profile."""
        async with self._sessions() as db:
            row = await db.get(JournalNodeRow, node_id)
            return _node_to_domain(row) if row and row.profile_id == profile_id else None

    async def list_nodes(
        self, profile_id: UUID, kinds: frozenset[NodeKind] | None = None
    ) -> list[JournalNode]:
        """The profile's nodes, oldest first."""
        query = select(JournalNodeRow).where(JournalNodeRow.profile_id == profile_id)
        if kinds is not None:
            query = query.where(JournalNodeRow.kind.in_([kind.value for kind in kinds]))
        async with self._sessions() as db:
            rows = await db.scalars(query.order_by(JournalNodeRow.created_at))
            return [_node_to_domain(row) for row in rows]

    async def list_entries(
        self, profile_id: UUID, date_from: date | None = None, date_to: date | None = None
    ) -> list[JournalNode]:
        """Entries between two dates, newest first."""
        query = select(JournalNodeRow).where(
            JournalNodeRow.profile_id == profile_id, JournalNodeRow.kind == NodeKind.ENTRY.value
        )
        if date_from is not None:
            query = query.where(JournalNodeRow.entry_date >= date_from)
        if date_to is not None:
            query = query.where(JournalNodeRow.entry_date <= date_to)
        async with self._sessions() as db:
            rows = await db.scalars(
                query.order_by(JournalNodeRow.entry_date.desc(), JournalNodeRow.created_at.desc())
            )
            return [_node_to_domain(row) for row in rows]

    async def delete_node(self, profile_id: UUID, node_id: UUID) -> bool:
        """Delete a node; its links go with it."""
        async with self._sessions() as db, db.begin():
            result = await db.execute(
                delete(JournalNodeRow).where(
                    JournalNodeRow.id == node_id, JournalNodeRow.profile_id == profile_id
                )
            )
            return result.rowcount > 0

    async def add_link(self, link: JournalLink) -> None:
        """Store a new link. The unique key refuses a second `(from_id, to_id, kind)`."""
        async with self._sessions() as db, db.begin():
            db.add(_link_to_row(link))

    async def update_link(self, link: JournalLink) -> None:
        """Save a link's status and reason."""
        async with self._sessions() as db, db.begin():
            await db.merge(_link_to_row(link))

    async def get_link(self, profile_id: UUID, link_id: UUID) -> JournalLink | None:
        """One link of this profile."""
        async with self._sessions() as db:
            row = await db.get(JournalLinkRow, link_id)
            return _link_to_domain(row) if row and row.profile_id == profile_id else None

    async def list_links(self, profile_id: UUID) -> list[JournalLink]:
        """Every link of the profile, oldest first."""
        async with self._sessions() as db:
            rows = await db.scalars(
                select(JournalLinkRow)
                .where(JournalLinkRow.profile_id == profile_id)
                .order_by(JournalLinkRow.created_at)
            )
            return [_link_to_domain(row) for row in rows]

    async def delete_for_profile(self, profile_id: UUID) -> None:
        """Delete the profile's whole journal (the profile's own delete cascades too)."""
        async with self._sessions() as db, db.begin():
            await db.execute(delete(JournalNodeRow).where(JournalNodeRow.profile_id == profile_id))
