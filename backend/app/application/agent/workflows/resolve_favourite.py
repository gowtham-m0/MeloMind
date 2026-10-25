"""Workflow 2: resolve a favourite the user typed into Qloo entities by climbing the hint
ladder. A fixed LangGraph graph:

interpret → climb
"""

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.nodes.climb_ladder import climb_ladder
from app.application.agent.nodes.interpret import interpret
from app.application.agent.resolve_state import ResolveDeps, ResolveState


def build_resolve_graph(deps: ResolveDeps) -> CompiledStateGraph:
    """The resolve_favourite graph, with this run's dependencies injected into every node."""
    graph = StateGraph(ResolveState)
    graph.add_node("interpret", partial(interpret, deps=deps))
    graph.add_node("climb", partial(climb_ladder, deps=deps))
    graph.add_edge(START, "interpret")
    graph.add_edge("interpret", "climb")
    graph.add_edge("climb", END)
    return graph.compile(name="resolve_favourite")
