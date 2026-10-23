"""The agent log: one plain-English entry per decision, saved to the run as it happens."""

import logging
from uuid import UUID

from app.application.ports import AgentRunRepository
from app.domain.runs import AgentStep, StepLevel

logger = logging.getLogger(__name__)


class RunLog:
    """Writes steps to one agent run. Never pass keys, note text, lyrics or raw Qloo data."""

    def __init__(self, runs: AgentRunRepository, run_id: UUID) -> None:
        self._runs = runs
        self.run_id = run_id

    async def info(self, node: str, message: str) -> None:
        """A normal step."""
        await self._write(AgentStep(node=node, message=message))

    async def warn(self, node: str, message: str) -> None:
        """Something went wrong and the agent recovered from it."""
        await self._write(AgentStep(node=node, message=message, level=StepLevel.WARNING))

    async def _write(self, step: AgentStep) -> None:
        logger.info("[%s] %s: %s", self.run_id, step.node, step.message)
        await self._runs.append_step(self.run_id, step)
