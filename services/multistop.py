"""route_multi — one walk for a whole basket (lld.md §10).

Floors are cleared highest first, one picking pass each, and the walk ends at a till, so a
shopper never climbs twice (FR-17, FR-18). Within a floor, ambient stops come first and chilled
stops last (EC-33), each sequenced by nearest neighbour and then open-path 2-opt.
"""

import math

from models.domain import BasketItem, Excluded, MultiRoute, NoRoute, Placement, Stop
from services.planogram import Planogram
from services.routing import RouteEngine

EPSILON = 1e-9


def nn_then_2opt(engine: RouteEngine, entry: str, stops: list, step_free: bool, improve=True):
    """Order ``stops`` (anything with ``node_id``) as an open path from a fixed ``entry``.

    The 2-opt compares whole open-path lengths, so there is no wrap-around term back to the
    entry, and a reversed segment on a one-way edge is costed in its new direction.
    """

    def d(a: str, b: str) -> float:
        return engine.distance(a, b, step_free)

    seq, pool, cur = [], list(stops), entry
    while pool:  # nearest neighbour
        nxt = min(pool, key=lambda s: (d(cur, s.node_id), s.node_id))
        seq.append(nxt)
        pool.remove(nxt)
        cur = nxt.node_id

    def length(order) -> float:
        nodes = [entry] + [s.node_id for s in order]
        return sum(d(a, b) for a, b in zip(nodes, nodes[1:], strict=False))

    improved = improve
    while improved:  # 2-opt, OPEN variant — reversing any segment, the first stop included
        improved = False
        best = length(seq)
        for i in range(len(seq) - 1):
            for j in range(i + 1, len(seq)):
                candidate = seq[:i] + seq[i : j + 1][::-1] + seq[j + 1 :]
                cost = length(candidate)
                if cost < best - EPSILON:
                    seq, best, improved = candidate, cost, True
    return seq


def _choose(engine, planogram, routable, start, step_free):
    """One placement per SKU. A SKU held in several places takes one on a floor the basket
    already visits, nearest the start, so a second placement never adds a floor."""
    graph = engine.graph
    open_ = {
        i.sku: [p for p in planogram.for_sku(i.sku) if p.node_id in graph.index] for i in routable
    }
    fixed_floors = {
        graph.nodes[ps[0].node_id].level
        for ps in open_.values()
        if len({graph.nodes[p.node_id].level for p in ps}) == 1
    }
    stops, excluded = [], []
    for item in routable:
        reachable = [
            p
            for p in open_[item.sku]
            if math.isfinite(engine.distance(start, p.node_id, step_free))
        ]
        if not reachable:
            excluded.append(
                Excluded(
                    item.sku,
                    "no_step_free_route",
                    f"There is no step-free route to {item.name} right now, so it is left "
                    "out of the route.",
                )
            )
            continue
        preferred = [p for p in reachable if graph.nodes[p.node_id].level in fixed_floors]
        best: Placement = min(
            preferred or reachable,
            key=lambda p: (engine.distance(start, p.node_id, step_free), p.node_id),
        )
        stops.append(Stop(item.sku, best, graph.nodes[best.node_id].level))
    return stops, excluded


def route_multi(
    engine: RouteEngine,
    planogram: Planogram,
    items: list[BasketItem],
    start: str,
    step_free: bool = False,
    improve: bool = True,
) -> MultiRoute | NoRoute:
    graph = engine.graph
    engine.distance(start, start)  # an unknown start is a bug — raises InvalidNodeError
    excluded = [Excluded(i.sku, i.reason, i.message) for i in items if not i.routable]
    stops, unreachable = _choose(
        engine, planogram, [i for i in items if i.routable], start, step_free
    )
    excluded += unreachable
    if not stops:
        return NoRoute("nothing_routable", "Nothing in the basket can be routed right now.")

    def d(a, b):
        return engine.distance(a, b, step_free)

    ordered, cursor = [], start
    for level in sorted({s.level for s in stops}, reverse=True):  # highest floor first
        cores = [
            n for n, node in graph.nodes.items() if node.level == level and node.node_type == "core"
        ]
        same_floor = graph.nodes[cursor].level == level
        entry = cursor if same_floor or not cores else min(cores, key=lambda c: (d(cursor, c), c))
        here = [s for s in stops if s.level == level]
        ambient = [s for s in here if s.placement.location_type != "CHILLER"]
        chilled = [s for s in here if s.placement.location_type == "CHILLER"]
        floor = nn_then_2opt(engine, entry, ambient, step_free, improve)
        floor += nn_then_2opt(
            engine, floor[-1].node_id if floor else entry, chilled, step_free, improve
        )
        ordered += floor
        cursor = ordered[-1].node_id

    tills = [n for n, node in graph.nodes.items() if node.node_type == "till"]
    till = min(tills, key=lambda t: (d(cursor, t), t))
    waypoints = [start] + [s.placement.node_id for s in ordered] + [till]
    nodes, stop_at = [start], []
    for a, b in zip(waypoints, waypoints[1:], strict=False):
        nodes += engine.path(a, b, step_free)[1:]
        stop_at.append(len(nodes) - 1)
    stop_at.pop()  # the last waypoint is the till, not a stop
    distance = sum(d(a, b) for a, b in zip(waypoints, waypoints[1:], strict=False))
    floors = tuple(dict.fromkeys(graph.nodes[n].level for n in nodes))
    return MultiRoute(
        tuple(nodes),
        distance,
        tuple(ordered),
        till,
        floors,
        step_free,
        tuple(excluded),
        tuple(stop_at),
    )
