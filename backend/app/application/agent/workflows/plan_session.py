"""Workflow 1: plan a session. A fixed LangGraph graph where code sets the order:

load_context → research → (fallback, only when needed) → select_items → resolve_media →
guardrails → compose
"""

from functools import partial
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.deps import PlanDeps
from app.application.agent.nodes.compose import compose
from app.application.agent.nodes.fallback import fallback
from app.application.agent.nodes.guardrails import guardrails
from app.application.agent.nodes.load_context import load_context
from app.application.agent.nodes.research import research
from app.application.agent.nodes.resolve_media import resolve_media
from app.application.agent.nodes.select_items import select_items
from app.application.agent.state import PlanState


def after_research(state: PlanState) -> Literal["fallback", "select_items"]:
    """Skip the fallback only when research succeeded with enough candidates."""
    return "select_items" if state.get("research_outcome") == "ok" else "fallback"


def build_plan_session(deps: PlanDeps) -> CompiledStateGraph:
    """The plan_session graph, with this run's dependencies injected into every node."""
    graph = StateGraph(PlanState)
    graph.add_node("load_context", partial(load_context, deps=deps))
    graph.add_node("research", partial(research, deps=deps))
    graph.add_node("fallback", partial(fallback, deps=deps))
    graph.add_node("select_items", partial(select_items, deps=deps))
    graph.add_node("resolve_media", partial(resolve_media, deps=deps))
    graph.add_node("guardrails", partial(guardrails, deps=deps))
    graph.add_node("compose", partial(compose, deps=deps))
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "research")
    graph.add_conditional_edges("research", after_research, ["fallback", "select_items"])
    graph.add_edge("fallback", "select_items")
    graph.add_edge("select_items", "resolve_media")
    graph.add_edge("resolve_media", "guardrails")
    graph.add_edge("guardrails", "compose")
    graph.add_edge("compose", END)
    return graph.compile(name="plan_session")
