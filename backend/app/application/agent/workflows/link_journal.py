"""Workflow 3: suggest links for a journal entry, for the user to confirm. A fixed LangGraph
graph:

extract → resolve → match → save
"""

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.nodes.extract_mentions import extract_mentions
from app.application.agent.nodes.match_nodes import match_nodes
from app.application.agent.nodes.resolve_mentions import resolve_mentions
from app.application.agent.nodes.save_suggestions import save_suggestions
from app.application.agent.resolve_state import LinkDeps, LinkState


def build_link_graph(deps: LinkDeps) -> CompiledStateGraph:
    """The link_journal graph, with this run's dependencies injected into every node."""
    graph = StateGraph(LinkState)
    graph.add_node("extract", partial(extract_mentions, deps=deps))
    graph.add_node("resolve", partial(resolve_mentions, deps=deps))
    graph.add_node("match", partial(match_nodes, deps=deps))
    graph.add_node("save", partial(save_suggestions, deps=deps))
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "resolve")
    graph.add_edge("resolve", "match")
    graph.add_edge("match", "save")
    graph.add_edge("save", END)
    return graph.compile(name="link_journal")
