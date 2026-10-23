"""The planner: runs the plan_session workflow for one session and returns its items."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.application.agent.deps import AgentLimits, PlanDeps
from app.application.agent.log import RunLog
from app.application.agent.workflows.plan_session import build_plan_session
from app.application.modes.base import SessionMode
from app.application.ports import (
    AgentRunRepository,
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    LanguageModel,
    MediaResolver,
    TasteGraph,
)
from app.domain.models import Profile
from app.domain.sessions import SessionItem


@dataclass(frozen=True)
class PlanRequest:
    """One plan to make: whose, which mode, how long, and the run that logs it."""

    profile: Profile
    mode: SessionMode
    target_minutes: int
    run_id: UUID


@dataclass(frozen=True)
class PlanResult:
    """The planned items, in order, and a small summary for the run's result."""

    items: list[SessionItem]
    summary: dict[str, Any]


class AgentPlanner:
    """Builds the workflow with this run's dependencies and runs it."""

    def __init__(
        self,
        *,
        feedback: FeedbackRepository,
        exclusions: ExclusionRepository,
        taste: TasteGraph,
        media: MediaResolver,
        runs: AgentRunRepository,
        limits: AgentLimits,
        language_model: LanguageModel | None = None,
        chat_models: ChatModels | None = None,
    ) -> None:
        self._feedback = feedback
        self._exclusions = exclusions
        self._taste = taste
        self._media = media
        self._runs = runs
        self._limits = limits
        self._language_model = language_model
        self._chat_models = chat_models

    async def plan(self, request: PlanRequest) -> PlanResult:
        """Run plan_session to the end. A result is always produced unless a port breaks."""
        deps = PlanDeps(
            feedback=self._feedback,
            exclusions=self._exclusions,
            taste=self._taste,
            media=self._media,
            log=RunLog(self._runs, request.run_id),
            mode=request.mode,
            limits=self._limits,
            target_minutes=request.target_minutes,
            language_model=self._language_model,
            chat_models=self._chat_models,
        )
        final = await build_plan_session(deps).ainvoke({"profile": request.profile})
        items: list[SessionItem] = final.get("items", [])
        return PlanResult(
            items=items,
            summary={
                "research_outcome": final.get("research_outcome"),
                "fallback_attempts": final.get("fallback_attempts", 0),
                "media_errors": final.get("media_errors", 0),
                "item_count": len(items),
                "total_duration_s": sum(item.duration_s for item in items),
                "source": self._taste.source,
            },
        )
