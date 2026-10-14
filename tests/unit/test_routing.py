"""Route engine tests. AC-04 is proven against a Dijkstra written here, from the raw edge rows,
sharing no code with the engine."""

import heapq
import math
import random
from pathlib import Path

import pytest

from errors import InvalidNodeError
from models.domain import NoRoute, Route
from services.planogram import Planogram
from services.routing import RouteEngine
from services.storegraph import StoreGraph
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"
COKE = "7123456"


@pytest.fixture(scope="module")
def demo():
    return load_store(DEMO)


@pytest.fixture(scope="module")
def engine(demo):
    return RouteEngine(StoreGraph(demo))


def independent_shortest(store, source, step_free=False, closed=()):
    """Textbook Dijkstra over the open edge rows — effective weight = weight + penalty."""
    open_nodes = {n for n, node in store.nodes.items() if node.is_open}
    arcs = {n: [] for n in open_nodes}
    for e in store.edges:
        if not e.is_open or e.edge_id in closed or (step_free and not e.step_free):
            continue
        if e.from_node in open_nodes and e.to_node in open_nodes:
            w = e.weight_m + e.penalty_m
            arcs[e.from_node].append((e.to_node, w))
            if e.bidirectional:
                arcs[e.to_node].append((e.from_node, w))
    dist, heap = {source: 0.0}, [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in arcs[u]:
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return dist


def path_length(engine, nodes, step_free=False):
    return sum(e.weight_m + e.penalty_m for e in engine.hops(nodes, step_free))


class TestShortestRoutes:
    """AC-04, FR-13 — every distance equals one computed independently from the store map."""

    @pytest.mark.parametrize("step_free", [False, True])
    def test_all_distances_from_50_starts_match(self, demo, engine, step_free):
        starts = random.Random(4).sample(sorted(engine.graph.index), 50)
        for s in starts:
            truth = independent_shortest(demo, s, step_free)
            for t in engine.graph.index:
                assert engine.distance(s, t, step_free) == pytest.approx(truth[t], abs=1e-9)

    def test_a_path_walks_its_own_distance(self, engine):
        nodes = engine.path("F0-ENTRANCE", "F2-A05-R04")
        assert nodes[0] == "F0-ENTRANCE" and nodes[-1] == "F2-A05-R04"
        assert path_length(engine, nodes) == pytest.approx(
            engine.distance("F0-ENTRANCE", "F2-A05-R04")
        )


def test_ac_06_fr_15_two_start_points_give_two_correct_routes(demo, engine):
    placements = Planogram(demo).for_sku(COKE)
    a = engine.route_single("F0-ENTRANCE", placements)
    b = engine.route_single("F2-A10-S", placements)
    assert isinstance(a, Route) and isinstance(b, Route)
    assert a.nodes != b.nodes
    for start, route in (("F0-ENTRANCE", a), ("F2-A10-S", b)):
        truth = independent_shortest(demo, start)
        assert route.distance_m == pytest.approx(min(truth[p.node_id] for p in placements))
        assert route.nodes[0] == start


def test_ac_21_fr_11_ec_20_the_route_goes_to_the_nearer_placement(demo, engine):
    placements = Planogram(demo).for_sku(COKE)
    near_end_cap = engine.route_single("F1-A08-N", placements)
    near_home = engine.route_single("F1-A07-R04", placements)
    assert near_end_cap.placement.node_id == "F1-A07-N"
    assert near_home.placement.node_id == "F1-A07-R03"


def test_ec_25_already_at_the_rack_is_a_zero_length_route(demo, engine):
    route = engine.route_single("F1-A07-R03", Planogram(demo).for_sku(COKE))
    assert (route.nodes, route.distance_m) == (("F1-A07-R03",), 0.0)


class TestStepFree:
    """AC-07, FR-19 — lifts only, or an honest no."""

    def test_a_step_free_route_uses_lifts_and_no_stairs(self, engine):
        nodes = engine.path("F0-ENTRANCE", "F2-A05-R04", step_free=True)
        hops = engine.hops(nodes, step_free=True)
        assert all(h.step_free for h in hops)
        level_changes = [h for h in hops if h.kind in ("lift", "stairs", "escalator")]
        assert [h.kind for h in level_changes] == ["lift", "lift"]

    def test_fr_14_the_ordinary_route_may_take_the_stairs(self, engine):
        hops = engine.hops(engine.path("F0-ENTRANCE", "F2-A05-R04"))
        assert "stairs" in {h.kind for h in hops}  # stairs 11 m beat a lift's 6 m + 25 m wait

    def test_ec_31_no_step_free_path_is_said_plainly(self, demo, engine):
        upper_lifts = [
            e.edge_id for e in demo.edges if e.kind == "lift" and e.from_node.startswith("F1-")
        ]
        closed = engine.closed(upper_lifts)
        placements = Planogram(demo).for_sku(_sku(demo, "Everyday Shampoo"))
        refusal = closed.route_single("F0-ENTRANCE", placements, step_free=True)
        assert isinstance(refusal, NoRoute) and refusal.reason == "no_step_free_route"
        assert "step-free" in refusal.message
        assert isinstance(closed.route_single("F0-ENTRANCE", placements), Route)


def _sku(demo, name):
    return next(p.sku for p in demo.products.values() if p.name == name)


def test_ec_30_a_closed_lift_is_routed_around_by_the_other_core(demo, engine):
    front = [e.edge_id for e in demo.edges if e.kind == "lift" and "FRONT" in e.from_node]
    closed = engine.closed(front)
    nodes = closed.path("F0-ENTRANCE", "F2-A01-R01", step_free=True)
    assert "F1-CORE-REAR" in nodes and "F1-CORE-FRONT" not in nodes
    truth = independent_shortest(demo, "F0-ENTRANCE", step_free=True, closed=set(front))
    assert closed.distance("F0-ENTRANCE", "F2-A01-R01", True) == pytest.approx(truth["F2-A01-R01"])


def test_ec_32_a_placement_on_a_closed_node_is_not_routable(demo, tmp_path):
    import shutil

    from datagen.build import STORE_ID

    copy = tmp_path / STORE_ID
    shutil.copytree(DEMO, copy)
    nodes = (copy / "map_nodes.csv").read_text()
    row = next(ln for ln in nodes.splitlines() if ln.startswith("F0-CTR-02,"))
    (copy / "map_nodes.csv").write_text(nodes.replace(row, row.rsplit(",", 1)[0] + ",false"))
    store = load_store(copy)
    engine = RouteEngine(StoreGraph(store))
    salmon = Planogram(store).for_sku(_sku(store, "Salmon Fillet"))
    refusal = engine.route_single("F0-ENTRANCE", salmon)
    assert isinstance(refusal, NoRoute) and refusal.reason == "no_open_location"


def test_ec_29_an_unknown_start_point_is_a_bug_not_a_guess(engine):
    with pytest.raises(InvalidNodeError):
        engine.distance("F9-NOWHERE", "F0-ENTRANCE")


def test_fr_19_step_free_graph_filters_before_collapsing_parallel_edges(engine):
    """The rear core joins F0 and F1 by stairs (11 m) and a lift (31 m effective). Taking the
    minimum first would leave the step-free graph with stairs, or with nothing."""
    a, b = "F0-CORE-REAR", "F1-CORE-REAR"
    assert engine.distance(a, b) == pytest.approx(11.0)
    assert engine.distance(a, b, step_free=True) == pytest.approx(31.0)
    assert engine.hops([a, b], step_free=True)[0].kind == "lift"
