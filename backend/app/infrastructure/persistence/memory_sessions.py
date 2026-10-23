"""`SessionRepository` in memory: for tests, and for local runs without `DATABASE_URL`."""

from copy import deepcopy
from uuid import UUID

from app.domain.sessions import Session, SessionStatus


class InMemorySessionRepository:
    """Keeps copies of sessions in a dict, so callers can't change stored data by accident."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}

    async def add(self, session: Session) -> None:
        """Store a new session and its items."""
        self._sessions[session.id] = deepcopy(session)

    async def get(self, session_id: UUID) -> Session | None:
        """One session with its items."""
        session = self._sessions.get(session_id)
        return deepcopy(session) if session else None

    async def update(self, session: Session) -> None:
        """Save the session and replace its items."""
        if session.id in self._sessions:
            self._sessions[session.id] = deepcopy(session)

    async def list_for_profile(
        self, profile_id: UUID, statuses: frozenset[SessionStatus] | None = None
    ) -> list[Session]:
        """The profile's sessions, newest first."""
        matching = [
            session
            for session in self._sessions.values()
            if session.profile_id == profile_id and (statuses is None or session.status in statuses)
        ]
        matching.sort(key=lambda session: session.created_at, reverse=True)
        return [deepcopy(session) for session in matching]
