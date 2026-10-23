"""The research agent: LangChain `create_agent`, bounded by middleware.

It compiles to a LangGraph graph and runs as the outer workflow's `research` node.
"""

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.deps import AgentLimits
from app.application.ports import ChatModels

# Room for submit_candidates on top of the Qloo calls. The tools also count Qloo calls
# themselves, and tell the agent to submit when the budget is spent.
SUBMIT_CALLS = 2
TOOL_RETRIES = 1
TOOL_RETRY_DELAY_SECONDS = 0.5
# Each turn passes through several middleware nodes, so the inner graph needs more steps.
RECURSION_LIMIT = 100


class ModelCallCounter(AgentMiddleware):
    """Counts model calls, so the log can say when the model-call limit ended research."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Count one call."""
        self.calls += 1
        return None


def build_research_agent(
    models: ChatModels,
    tools: Sequence[BaseTool],
    system_prompt: str,
    limits: AgentLimits,
    counter: ModelCallCounter,
) -> CompiledStateGraph:
    """The tool-calling agent, with call limits, retries for temporary errors and the backup
    model when the main one fails or times out."""
    middleware: list[AgentMiddleware] = [
        counter,
        ToolCallLimitMiddleware(
            run_limit=limits.max_tool_calls + SUBMIT_CALLS, exit_behavior="end"
        ),
        ModelCallLimitMiddleware(run_limit=limits.max_model_calls, exit_behavior="end"),
        ToolRetryMiddleware(
            max_retries=TOOL_RETRIES,
            retry_on=(TimeoutError, ConnectionError),
            on_failure="continue",
            initial_delay=TOOL_RETRY_DELAY_SECONDS,
            jitter=False,
        ),
    ]
    if models.fallback is not None:
        middleware.append(ModelFallbackMiddleware(models.fallback))
    return create_agent(
        models.primary,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=middleware,
        name="research",
    )
