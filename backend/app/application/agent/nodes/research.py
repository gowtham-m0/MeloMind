"""Step 2, `research` (AI agent): the agent gets the mode's brief, calls Qloo tools until it has
enough candidates, then submits them. On any error, limit or timeout it keeps what it found:
what it submitted, or else every recommendation Qloo gave it (still Qloo's picks, rule 9)."""

import asyncio
import logging

from langchain_core.messages import HumanMessage

from app.application.agent.deps import PlanDeps
from app.application.agent.prompts.research import research_system_prompt, research_task
from app.application.agent.research_agent import (
    RECURSION_LIMIT,
    ModelCallCounter,
    build_research_agent,
)
from app.application.agent.state import PlanState
from app.application.agent.tools.context import ToolContext
from app.application.agent.tools.research import research_tools
from app.application.agent.types import ResearchOutcome

logger = logging.getLogger(__name__)

NODE = "research"


async def research(state: PlanState, deps: PlanDeps) -> PlanState:
    """Run the research agent within its limits and record its outcome."""
    context = state["context"]
    brief = deps.mode.research_brief(context)
    if deps.chat_models is None:
        await deps.log.info(NODE, "No AI model is set up, so the rule-based plan will run.")
        return {"brief": brief, "candidates": [], "research_outcome": "skipped"}

    ctx = ToolContext(
        taste=deps.taste, log=deps.log, context=context, max_qloo_calls=deps.limits.max_tool_calls
    )
    counter = ModelCallCounter()
    agent = build_research_agent(
        deps.chat_models,
        research_tools(ctx),
        research_system_prompt(brief, context, deps.limits.max_tool_calls),
        deps.limits,
        counter,
    )
    budget = deps.limits.timeout_seconds
    await deps.log.info(NODE, f"Asked the AI agent to research. Cold-start tier {brief.tier}.")
    failure: ResearchOutcome | None = None
    try:
        await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [HumanMessage(content=research_task(brief))]},
                config={"recursion_limit": RECURSION_LIMIT},
            ),
            budget,
        )
    except TimeoutError:
        failure = "timeout"
    except Exception as exc:
        logger.warning("Research agent failed: %s", type(exc).__name__)
        failure = "error"

    candidates = list(ctx.submitted.values())
    outcome: ResearchOutcome
    if failure is None and deps.mode.has_enough(candidates):
        outcome = "ok"
    elif failure is not None:
        outcome = failure
    elif ctx.budget_used or counter.calls >= deps.limits.max_model_calls:
        outcome = "limit_hit"
    else:
        outcome = "too_few"
    kept = f"kept the {len(candidates)} candidates it had submitted"
    if not candidates and ctx.recommended:
        candidates = [ctx.seen[ref] for ref in ctx.recommended if ref in ctx.seen]
        kept = f"kept the {len(candidates)} recommendations Qloo had given it"
    await _log_outcome(deps, outcome, len(candidates), ctx, budget, kept)
    return {"brief": brief, "candidates": candidates, "research_outcome": outcome}


async def _log_outcome(
    deps: PlanDeps,
    outcome: ResearchOutcome,
    found: int,
    ctx: ToolContext,
    budget: float,
    kept: str,
) -> None:
    match outcome:
        case "ok":
            await deps.log.info(
                NODE, f"The agent submitted {found} candidates after {ctx.qloo_calls} Qloo calls."
            )
        case "timeout":
            await deps.log.warn(NODE, f"The agent ran out of time after {budget:.0f} s; {kept}.")
        case "error":
            await deps.log.warn(NODE, f"The agent stopped with an error; {kept}.")
        case "limit_hit":
            limit = (
                f"{deps.limits.max_tool_calls}-call Qloo limit"
                if ctx.budget_used
                else f"{deps.limits.max_model_calls}-step model limit"
            )
            await deps.log.warn(NODE, f"The agent hit its {limit}; {kept}.")
        case _:
            await deps.log.info(NODE, f"The agent submitted only {found} candidates.")
