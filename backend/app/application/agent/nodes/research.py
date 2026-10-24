"""Step 2, `research` (AI agent): the agent gets the brief, asks Qloo for each type, then
submits its best picks, which lead the feed. The pool is every recommendation Qloo gave it, so
the feed is full even when the agent stops early: on any error, limit or timeout it keeps what
it found (still Qloo's picks, rule 1)."""

import asyncio
import logging

from langchain_core.messages import HumanMessage

from app.application.agent.brief import build_brief, has_enough
from app.application.agent.deps import FeedDeps
from app.application.agent.prompts.research import research_system_prompt, research_task
from app.application.agent.research_agent import (
    RECURSION_LIMIT,
    ModelCallCounter,
    build_research_agent,
)
from app.application.agent.state import FeedState
from app.application.agent.tools.context import ToolContext
from app.application.agent.tools.research import research_tools
from app.application.agent.types import ResearchOutcome

logger = logging.getLogger(__name__)

NODE = "research"


async def research(state: FeedState, deps: FeedDeps) -> FeedState:
    """Run the research agent within its limits and record its outcome."""
    context = state["context"]
    brief = build_brief(context)
    if deps.chat_models is None:
        await deps.log.info(NODE, "No AI model is set up, so the rule-based picks will run.")
        return {"brief": brief, "pool": [], "research_outcome": "skipped", "qloo_calls": 0}

    ctx = ToolContext(
        taste=deps.taste, log=deps.log, context=context, max_qloo_calls=deps.limits.max_tool_calls
    )
    counter = ModelCallCounter()
    agent = build_research_agent(
        deps.chat_models,
        research_tools(ctx),
        research_system_prompt(brief, context, deps.limits.max_tool_calls, ctx.short),
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

    featured = list(ctx.submitted.values())
    others = [
        ctx.seen[ref] for ref in ctx.recommended if ref in ctx.seen and ref not in ctx.submitted
    ]
    candidates = featured + others
    outcome: ResearchOutcome
    if failure is None and has_enough(candidates):
        outcome = "ok"
    elif failure is not None:
        outcome = failure
    elif ctx.budget_used or counter.calls >= deps.limits.max_model_calls:
        outcome = "limit_hit"
    else:
        outcome = "too_few"
    kept = f"kept the {len(candidates)} recommendations Qloo had given it"
    await _log_outcome(deps, outcome, len(candidates), ctx, budget, kept)
    return {
        "brief": brief,
        "pool": candidates,
        "research_outcome": outcome,
        "qloo_calls": ctx.qloo_calls,
    }


async def _log_outcome(
    deps: FeedDeps,
    outcome: ResearchOutcome,
    found: int,
    ctx: ToolContext,
    budget: float,
    kept: str,
) -> None:
    match outcome:
        case "ok":
            await deps.log.info(
                NODE,
                f"The agent picked {len(ctx.submitted)} favourites from {found} results after "
                f"{ctx.qloo_calls} Qloo calls.",
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
