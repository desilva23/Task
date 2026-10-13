"""StateGraph assembly (lld.md §6). Eleven nodes on explicit edges; three call a model.

``describe_route → verify → END`` are plain edges, and every run that makes a claim reaches
``verify`` — there is no path from a composed answer to the page that skips it.
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from graph import routers
from graph.nodes.availability import make_check_availability
from graph.nodes.clarify import make_clarify
from graph.nodes.classify import make_classify_query
from graph.nodes.describe import make_describe_route
from graph.nodes.locations import make_resolve_locations
from graph.nodes.resolve_items import make_resolve_items
from graph.nodes.routes import make_route_multi, make_route_single
from graph.nodes.substitutes import make_suggest_substitutes
from graph.nodes.understand import make_understand_query
from graph.nodes.verify import make_verify
from graph.state import JourneyState

NODES = {
    "classify_query": make_classify_query,
    "understand_query": make_understand_query,  # model
    "resolve_items": make_resolve_items,
    "clarify": make_clarify,
    "check_availability": make_check_availability,
    "suggest_substitutes": make_suggest_substitutes,  # model
    "resolve_locations": make_resolve_locations,
    "route_single": make_route_single,
    "route_multi": make_route_multi,
    "describe_route": make_describe_route,  # model
    "verify": make_verify,
}


def build_graph(services, model, checkpointer=None):
    g = StateGraph(JourneyState)
    for name, make in NODES.items():
        g.add_node(name, make(services, model))

    g.add_conditional_edges(START, routers.after_start, ["classify_query", "resolve_locations"])
    g.add_conditional_edges(
        "classify_query", routers.after_classify, ["understand_query", "resolve_items", END]
    )
    g.add_edge("understand_query", "resolve_items")
    for source in ("resolve_items", "clarify"):
        g.add_conditional_edges(source, routers.after_resolve, ["clarify", "check_availability"])
    g.add_conditional_edges(
        "check_availability",
        routers.after_availability,
        ["suggest_substitutes", "resolve_locations"],
    )
    g.add_edge("suggest_substitutes", "resolve_locations")
    g.add_conditional_edges(
        "resolve_locations", routers.after_locations, ["verify", "route_single", "route_multi"]
    )
    g.add_edge("route_single", "describe_route")
    g.add_edge("route_multi", "describe_route")
    g.add_edge("describe_route", "verify")  # plain edge — the gate cannot be skipped
    g.add_edge("verify", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
