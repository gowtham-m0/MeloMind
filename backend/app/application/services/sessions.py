"""Use cases for sessions: planning in the background, the caregiver's review edits, and the
status changes planning → draft → approved → in progress → completed."""

import asyncio
import logging
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Protocol
from uuid import UUID

from app.application.agent.log import RunLog
from app.application.agent.planner import PlanRequest, PlanResult
from app.application.modes.registry import ModeRegistry
from app.application.ports import AgentRunRepository, ExclusionRepository, SessionRepository
from app.application.services.background import BackgroundRunner
from app.application.services.profiles import ProfileService
from app.application.services.rate_limit import SlidingWindowRateLimiter
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.domain.feedback import Blocklist
from app.domain.models import utc_now
from app.domain.runs import AgentRun, RunKind, RunStatus
from app.domain.sessions import Session, SessionStatus

logger = logging.getLogger(__name__)

TARGET_MINUTES = (10, 20, 30)
PROMPT_MAX = 300
# A plan that takes longer than this is stuck: the agent itself stops at 25 seconds.
PLAN_HARD_TIMEOUT_SECONDS = 90.0
NODE = "plan"

_ACTIONS = {
    SessionStatus.APPROVED: "approved",
    SessionStatus.IN_PROGRESS: "started",
    SessionStatus.COMPLETED: "completed",
}


class Planner(Protocol):
    """Makes the plan for one session (the agent's plan_session workflow)."""

    async def plan(self, request: PlanRequest) -> PlanResult:
        """The planned items. Raises when planning can't finish."""
        ...


class SessionService:
    """Sessions for their owner only: someone else's session is reported as not found."""

    def __init__(
        self,
        profiles: ProfileService,
        sessions: SessionRepository,
        runs: AgentRunRepository,
        exclusions: ExclusionRepository,
        planner: Planner,
        runner: BackgroundRunner,
        modes: ModeRegistry,
        rate_limiter: SlidingWindowRateLimiter,
    ) -> None:
        self._profiles = profiles
        self._sessions = sessions
        self._runs = runs
        self._exclusions = exclusions
        self._planner = planner
        self._runner = runner
        self._modes = modes
        self._rate_limiter = rate_limiter

    async def plan(
        self,
        owner_id: UUID,
        profile_id: UUID,
        mode_name: str,
        target_minutes: int,
        *,
        count_towards_limit: bool = True,
    ) -> Session:
        """Start planning in the background. Returns at once, with status `planning`."""
        profile = await self._profiles.get(owner_id, profile_id)
        mode = self._modes.get(mode_name)
        if target_minutes not in TARGET_MINUTES:
            raise InvalidInputError("The session length must be 10, 20 or 30 minutes.")
        if count_towards_limit:
            self._rate_limiter.check(owner_id)
        run = AgentRun(profile_id=profile.id, kind=RunKind.PLAN)
        session = Session(
            profile_id=profile.id,
            mode=mode.name,
            target_minutes=target_minutes,
            agent_run_id=run.id,
        )
        await self._runs.add(run)
        await self._sessions.add(session)
        request = PlanRequest(
            profile=profile, mode=mode, target_minutes=target_minutes, run_id=run.id
        )
        await self._runner.spawn(partial(self._execute, session.id, request))
        return await self.get(owner_id, session.id)

    async def get(self, owner_id: UUID, session_id: UUID) -> Session:
        """One session with its items."""
        session = await self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("Session not found.")
        try:
            await self._profiles.get(owner_id, session.profile_id)
        except NotFoundError:
            raise NotFoundError("Session not found.") from None
        return session

    async def history(self, owner_id: UUID, profile_id: UUID) -> list[Session]:
        """The profile's sessions and warm-up sets, newest first."""
        await self._profiles.get(owner_id, profile_id)
        return await self._sessions.list_for_profile(profile_id)

    async def edit_items(
        self,
        owner_id: UUID,
        session_id: UUID,
        order: Sequence[UUID] | None = None,
        removed: Sequence[UUID] | None = None,
        prompts: Mapping[UUID, str] | None = None,
    ) -> Session:
        """Remove items, reorder them or change prompts, while the session is a draft."""
        session = await self.get(owner_id, session_id)
        if session.status is not SessionStatus.DRAFT:
            raise ConflictError("Only a draft can be changed.")
        ids = {item.id for item in session.items}
        gone = set(removed or ())
        if not gone <= ids:
            raise InvalidInputError("Some removed items aren't in this session.")
        session.items = [item for item in session.items if item.id not in gone]
        if order is not None:
            by_id = {item.id: item for item in session.items}
            if len(order) != len(by_id) or set(order) != set(by_id):
                raise InvalidInputError("The order must list every remaining item once.")
            session.items = [by_id[item_id] for item_id in order]
        if prompts:
            if session.is_warmup:
                raise InvalidInputError("The warm-up set has no prompts.")
            by_id = {item.id: item for item in session.items}
            for item_id, text in prompts.items():
                if item_id not in by_id:
                    raise InvalidInputError("Some prompts are for items that aren't here.")
                by_id[item_id].prompt = " ".join(text.split())[:PROMPT_MAX] or None
        session.renumber()
        return await self._save(session)

    async def approve(self, owner_id: UUID, session_id: UUID) -> Session:
        """The caregiver approves the draft. Only approved items can reach Person mode."""
        session = await self.get(owner_id, session_id)
        if session.status is SessionStatus.DRAFT and not session.items:
            raise InvalidInputError("Keep at least one item before approving.")
        return await self._move(session, SessionStatus.APPROVED)

    async def start(self, owner_id: UUID, session_id: UUID) -> Session:
        """The caregiver starts playing an approved session."""
        return await self._move(await self.get(owner_id, session_id), SessionStatus.IN_PROGRESS)

    async def complete(self, owner_id: UUID, session_id: UUID) -> Session:
        """The session is over."""
        return await self._move(await self.get(owner_id, session_id), SessionStatus.COMPLETED)

    async def _move(self, session: Session, status: SessionStatus) -> Session:
        if not session.can_move_to(status):
            state = session.status.value.replace("_", " ")
            raise ConflictError(f"A session that is {state} can't be {_ACTIONS[status]}.")
        session.status = status
        return await self._save(session)

    async def _save(self, session: Session) -> Session:
        session.updated_at = utc_now()
        await self._sessions.update(session)
        return session

    async def _execute(self, session_id: UUID, request: PlanRequest) -> None:
        """The background part of `plan`: run the agent and store the draft."""
        log = RunLog(self._runs, request.run_id)
        try:
            result = await asyncio.wait_for(self._planner.plan(request), PLAN_HARD_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("Planning failed")
            await self._fail(session_id, log, "Planning failed. Please try again.")
            return
        # Something may have been rejected while the agent worked: check once more.
        blocklist = Blocklist.from_exclusions(
            await self._exclusions.list_for_profile(request.profile.id)
        )
        items = [item for item in result.items if not blocklist.blocks(item.ref, item.title)]
        if not items:
            await self._fail(session_id, log, "Nothing playable was found. Please try again.")
            return
        session = await self._sessions.get(session_id)
        if session is None:
            return
        session.items = items
        session.renumber()
        session.status = SessionStatus.DRAFT
        await self._save(session)
        minutes = round(session.total_duration_s / 60)
        what = "Warm-up set" if session.is_warmup else "Draft"
        await log.info(
            NODE,
            f"{what} ready for review: {len(session.items)} items, about {minutes} min.",
        )
        await self._runs.finish(
            request.run_id, RunStatus.DONE, {"session_id": str(session_id), **result.summary}
        )

    async def _fail(self, session_id: UUID, log: RunLog, message: str) -> None:
        session = await self._sessions.get(session_id)
        if session is not None:
            session.status = SessionStatus.FAILED
            await self._save(session)
        await log.warn(NODE, message)
        await self._runs.finish(log.run_id, RunStatus.FAILED, {"session_id": str(session_id)})
