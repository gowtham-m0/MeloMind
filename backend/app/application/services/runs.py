"""Reading agent runs: the log the user watches while the agent works."""

from uuid import UUID

from app.application.ports import AgentRunRepository
from app.application.services.profiles import ProfileService
from app.core.errors import NotFoundError
from app.domain.runs import AgentRun


class AgentRunService:
    """Agent runs for their owner only."""

    def __init__(self, profiles: ProfileService, runs: AgentRunRepository) -> None:
        self._profiles = profiles
        self._runs = runs

    async def get(self, owner_id: UUID, run_id: UUID) -> AgentRun:
        """One run with its log. Someone else's run is reported as not found."""
        run = await self._runs.get(run_id)
        if run is None:
            raise NotFoundError("Agent run not found.")
        try:
            await self._profiles.get(owner_id, run.profile_id)
        except NotFoundError:
            raise NotFoundError("Agent run not found.") from None
        return run
