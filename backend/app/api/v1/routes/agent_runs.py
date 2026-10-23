"""Agent run route: the log the frontend polls while the agent works."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, RunServiceDep
from app.api.v1.schemas.agent_runs import AgentRunOut

router = APIRouter(prefix="/agent-runs", tags=["agent runs"])


@router.get("/{run_id}")
async def get_agent_run(run_id: UUID, user: CurrentUserDep, runs: RunServiceDep) -> AgentRunOut:
    """One run, its status and its plain-English log."""
    return AgentRunOut.from_domain(await runs.get(user.id, run_id))
