"""`SessionRepository` on Postgres with SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import EntityType
from app.domain.sessions import ItemSource, MediaRef, Session, SessionItem, SessionStatus
from app.infrastructure.persistence.models import SessionItemRow, SessionRow


def _item_to_domain(row: SessionItemRow) -> SessionItem:
    media = None
    if row.media_provider and row.media_ref and row.media_duration_s is not None:
        media = MediaRef(
            provider=row.media_provider,
            ref=row.media_ref,
            duration_s=row.media_duration_s,
            title=row.media_title or "",
        )
    return SessionItem(
        id=row.id,
        position=row.position,
        ref=row.ref,
        title=row.title,
        entity_type=EntityType(row.entity_type),
        source=ItemSource(row.source),
        reason=row.reason,
        signal=row.signal,
        release_year=row.release_year,
        age_at_release=row.age_at_release,
        prompt=row.prompt,
        media=media,
        duration_s=row.duration_s,
    )


def _copy_item(item: SessionItem, row: SessionItemRow) -> None:
    row.position = item.position
    row.ref = item.ref
    row.title = item.title
    row.entity_type = item.entity_type.value
    row.source = item.source.value
    row.reason = item.reason
    row.signal = item.signal
    row.release_year = item.release_year
    row.age_at_release = item.age_at_release
    row.prompt = item.prompt
    row.media_provider = item.media.provider if item.media else None
    row.media_ref = item.media.ref if item.media else None
    row.media_title = item.media.title if item.media else None
    row.media_duration_s = item.media.duration_s if item.media else None
    row.duration_s = item.duration_s


def _item_to_row(item: SessionItem, session_id: UUID) -> SessionItemRow:
    row = SessionItemRow(id=item.id, session_id=session_id)
    _copy_item(item, row)
    return row


def _session_to_domain(row: SessionRow) -> Session:
    return Session(
        id=row.id,
        profile_id=row.profile_id,
        mode=row.mode,
        target_minutes=row.target_minutes,
        status=SessionStatus(row.status),
        agent_run_id=row.agent_run_id,
        items=[_item_to_domain(item) for item in row.items],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresSessionRepository:
    """Sessions and their items in Postgres. The database cascades profile deletes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, session: Session) -> None:
        """Store a new session and its items."""
        async with self._sessions() as db, db.begin():
            db.add(
                SessionRow(
                    id=session.id,
                    profile_id=session.profile_id,
                    mode=session.mode,
                    target_minutes=session.target_minutes,
                    status=session.status.value,
                    agent_run_id=session.agent_run_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    items=[_item_to_row(item, session.id) for item in session.items],
                )
            )

    async def get(self, session_id: UUID) -> Session | None:
        """One session with its items."""
        async with self._sessions() as db:
            row = await db.get(SessionRow, session_id)
            return _session_to_domain(row) if row else None

    async def update(self, session: Session) -> None:
        """Save the session; items keep their rows by ID, and removed items are deleted."""
        async with self._sessions() as db, db.begin():
            row = await db.get(SessionRow, session.id)
            if row is None:
                return
            row.status = session.status.value
            row.agent_run_id = session.agent_run_id
            row.updated_at = session.updated_at
            existing = {item.id: item for item in row.items}
            rows: list[SessionItemRow] = []
            for item in session.items:
                item_row = existing.get(item.id)
                if item_row is None:
                    item_row = _item_to_row(item, session.id)
                else:
                    _copy_item(item, item_row)
                rows.append(item_row)
            row.items = rows

    async def list_for_profile(
        self, profile_id: UUID, statuses: frozenset[SessionStatus] | None = None
    ) -> list[Session]:
        """The profile's sessions, newest first."""
        query = select(SessionRow).where(SessionRow.profile_id == profile_id)
        if statuses is not None:
            query = query.where(SessionRow.status.in_([status.value for status in statuses]))
        async with self._sessions() as db:
            rows = await db.scalars(query.order_by(SessionRow.created_at.desc()))
            return [_session_to_domain(row) for row in rows]
