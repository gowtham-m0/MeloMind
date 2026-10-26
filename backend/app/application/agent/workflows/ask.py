"""The ask run: the build_feed workflow's tail, aimed at one extra row.

load_context → ask_row → guardrails → decorate

It reuses `load_context`, `guardrails` and `decorate` unchanged, so an ask row follows the same
rules as the feed (rules 1 to 3): a source and a reason on every item, nothing excluded, once each.
It's the research step of build_feed pointed at the user's request, not a second agent.
"""

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.application.agent.deps import FeedDeps
from app.application.agent.nodes.ask_row import ask_row
from app.application.agent.nodes.decorate import decorate
from app.application.agent.nodes.guardrails import guardrails
from app.application.agent.nodes.load_context import load_context
from app.application.agent.state import FeedState
from app.application.agent.types import AskIntent


def build_ask_graph(deps: FeedDeps, intent: AskIntent) -> CompiledStateGraph:
    """The ask graph, with this run's dependencies injected into every node."""
    graph = StateGraph(FeedState)
    graph.add_node("load_context", partial(load_context, deps=deps))
    graph.add_node("ask_row", partial(ask_row, deps=deps, intent=intent))
    graph.add_node("guardrails", partial(guardrails, deps=deps))
    graph.add_node("decorate", partial(decorate, deps=deps))
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "ask_row")
    graph.add_edge("ask_row", "guardrails")
    graph.add_edge("guardrails", "decorate")
    graph.add_edge("decorate", END)
    return graph.compile(name="ask")
