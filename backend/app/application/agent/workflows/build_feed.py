"""Workflow 1: build the feed. A fixed LangGraph graph where code sets the order:

load_context → research → (fallback, only when needed) → build_rows → add_songs → guardrails →
decorate → explain
"""

from functools import partial
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.deps import FeedDeps
from app.application.agent.nodes.add_songs import add_songs
from app.application.agent.nodes.build_rows import build_rows
from app.application.agent.nodes.decorate import decorate
from app.application.agent.nodes.explain import explain
from app.application.agent.nodes.fallback import fallback
from app.application.agent.nodes.guardrails import guardrails
from app.application.agent.nodes.load_context import load_context
from app.application.agent.nodes.research import research
from app.application.agent.state import FeedState


def after_research(state: FeedState) -> Literal["fallback", "build_rows"]:
    """Skip the fallback only when research succeeded with enough of every type."""
    return "build_rows" if state.get("research_outcome") == "ok" else "fallback"


def build_feed_graph(deps: FeedDeps) -> CompiledStateGraph:
    """The build_feed graph, with this run's dependencies injected into every node."""
    graph = StateGraph(FeedState)
    graph.add_node("load_context", partial(load_context, deps=deps))
    graph.add_node("research", partial(research, deps=deps))
    graph.add_node("fallback", partial(fallback, deps=deps))
    graph.add_node("build_rows", partial(build_rows, deps=deps))
    graph.add_node("add_songs", partial(add_songs, deps=deps))
    graph.add_node("guardrails", partial(guardrails, deps=deps))
    graph.add_node("decorate", partial(decorate, deps=deps))
    graph.add_node("explain", partial(explain, deps=deps))
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "research")
    graph.add_conditional_edges("research", after_research, ["fallback", "build_rows"])
    graph.add_edge("fallback", "build_rows")
    graph.add_edge("build_rows", "add_songs")
    graph.add_edge("add_songs", "guardrails")
    graph.add_edge("guardrails", "decorate")
    graph.add_edge("decorate", "explain")
    graph.add_edge("explain", END)
    return graph.compile(name="build_feed")
