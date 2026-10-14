"""AC-09, FR-25, NFR-08 — AC-01 to AC-08, run unchanged against both store folders.

Nothing here names an aisle or a node of either store: expectations come from each store's own
data, so the same tests prove the same behaviour on a differently shaped store.
"""

from functools import cache
from pathlib import Path

import pytest

from graph.journey import Journey
from graph.model import NoModel, good_model
from graph.services import Services
from models.domain import Availability, NoRoute, Route
from tests.unit.test_routing import independent_shortest
from ui.view import addable, group_results
from validation import load_store

DATA = Path(__file__).resolve().parents[2] / "data"
STORES = ["SBY-DEMO-001", "SBY-PORT-002"]


@cache
def services(store_id):
    return Services.from_store(load_store(DATA / store_id))


@pytest.fixture(params=STORES)
def svc(request):
    return services(request.param)


@pytest.fixture(params=["model", "no-model"])
def journey(request, svc):
    return Journey(svc, good_model(svc) if request.param == "model" else NoModel())


def sku(svc, name):
    return next(p.sku for p in svc.store.products.values() if p.name == name)


def answer_first(j, thread, out):
    while out.pending:
        out = j.resume(
            thread, {q["index"]: q["options"][0]["sku"] for q in out.pending["questions"]}
        )
    return out


def top_floor_spot(svc):
    """An aisle end on the highest floor — a start point far from the entrance."""
    top = max(n.level for n in svc.store.nodes.values())
    return max(
        i for i, n in svc.store.nodes.items() if n.level == top and n.node_type == "aisle_end"
    )


def test_ac_09_ac_01_a_known_product_is_found_with_floor_aisle_rack_shelf(svc, journey):
    s = journey.run_query("a1", "Coca-Cola Classic").state
    coke = sku(svc, "Coca-Cola Classic")
    assert s["availability"][coke] == "in_stock" and s["verified"]
    for p in svc.planogram.for_sku(coke):
        node = svc.store.nodes[p.node_id]
        if p.shelf_no is not None:
            where = f"floor {node.level}, aisle {node.aisle}, rack {node.rack}, shelf {p.shelf_no}"
            assert where in " ".join(s["results"]).lower()


def test_ac_09_ac_02_three_products_then_one_route_covering_all(svc, journey):
    out = answer_first(journey, "a2", journey.run_query("a2", "milk, bread, eggs"))
    chosen = list(dict.fromkeys(out.state["resolved"].values()))
    assert len(out.state["term_status"]) == 3 and len(chosen) == 3
    route = journey.plan_route("a2r", chosen).state["route"]
    assert route["kind"] == "multi" and sorted(s["sku"] for s in route["stops"]) == sorted(
        k for k in chosen if svc.stock.availability(k) is Availability.IN_STOCK
    )


def test_ac_09_ac_03_one_choice_keeps_the_rest(svc, journey):
    out = journey.run_query("a3", "Coca-Cola Classic, milk, bananas")
    assert [q["term"] for q in out.pending["questions"]] == ["milk"]
    kept = dict(out.state["resolved"])
    out = answer_first(journey, "a3", out)
    assert {k: v for k, v in out.state["resolved"].items() if k in kept} == kept


def test_ac_09_ac_04_route_distance_is_the_true_shortest(svc):
    engine = svc.engine
    for name in ("Everyday Shampoo", "Salmon Fillet", "Coca-Cola Classic"):
        r = engine.route_single(engine.graph.entrance, svc.planogram.for_sku(sku(svc, name)))
        truth = independent_shortest(svc.store, engine.graph.entrance)
        assert r.distance_m == pytest.approx(truth[r.placement.node_id])


def test_ac_09_ac_05_every_floor_once_highest_first_ending_at_a_till(svc, journey):
    per_floor = {}
    for p in sorted(svc.store.placements, key=lambda p: p.sku):
        level = svc.store.nodes[p.node_id].level
        if p.location_type == "HOME" and svc.stock.availability(p.sku) is Availability.IN_STOCK:
            per_floor.setdefault(level, p.sku)
    route = journey.plan_route("a5", list(per_floor.values())).state["route"]
    levels = [svc.store.nodes[s["node_id"]].level for s in route["stops"]]
    assert levels == sorted(levels, reverse=True) and set(levels) == set(per_floor)
    assert svc.store.nodes[route["nodes"][-1]].node_type == "till"


def test_ac_09_ac_06_two_starts_two_correct_routes(svc):
    engine, placements = svc.engine, svc.planogram.for_sku(sku(svc, "Baked Beans"))
    starts = [engine.graph.entrance, top_floor_spot(svc)]
    routes = [engine.route_single(s, placements) for s in starts]
    assert routes[0].nodes != routes[1].nodes
    for start, r in zip(starts, routes, strict=True):
        assert r.distance_m == pytest.approx(min(independent_shortest(svc.store, start)[p.node_id]
                                                 for p in placements))  # fmt: skip


def test_ac_09_ac_07_step_free_uses_lifts_or_says_there_is_none(svc):
    engine = svc.engine
    target = svc.planogram.for_sku(sku(svc, "Everyday Shampoo"))
    r = engine.route_single(engine.graph.entrance, target, step_free=True)
    assert isinstance(r, Route)
    kinds = {h.kind for h in engine.hops(list(r.nodes), step_free=True)}
    assert "stairs" not in kinds and ("lift" in kinds or len(r.floors) == 1)
    lifts = [e.edge_id for e in svc.store.edges if e.kind == "lift"]
    refusal = engine.closed(lifts).route_single(engine.graph.entrance, target, step_free=True)
    if svc.store.nodes[r.placement.node_id].level > 0:
        assert isinstance(refusal, NoRoute) and refusal.reason == "no_step_free_route"


def test_ac_09_ac_08_grouped_and_one_action_adds_only_the_available(svc, journey):
    out = answer_first(
        journey, "a8", journey.run_query("a8", "bananas, baked beans, dental floss, diet coke")
    )
    groups = group_results(svc, out.state)
    assert len(groups.available) == 3 and [r.sku for r in groups.unavailable] == [
        sku(svc, "Diet Coke")
    ]
    assert addable(groups) == [r.sku for r in groups.available]
