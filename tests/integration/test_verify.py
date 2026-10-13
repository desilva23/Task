"""AC-10, NFR-02, EC-47 — a wrong claim never reaches the page.

Each test corrupts one claim — in the model's wording or in state itself — and checks the verify
gate blocks it, renders the template from the services instead, and records the mismatch.
"""

from functools import cache
from pathlib import Path

from graph.journey import Journey
from graph.model import FakeModel, good_model
from graph.nodes.verify import make_verify
from graph.services import Services
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def services():
    return Services.from_store(load_store(DEMO))


def describing(rewrite):
    good = good_model(services())

    def describe(schema, system, user):
        lines = good.complete("describe", schema, system, user)["lines"]
        return {"lines": [rewrite(line) for line in lines]}

    return FakeModel(
        understand=good.handlers["understand"],
        substitute=good.handlers["substitute"],
        describe=describe,
    )


def coke_route(model):
    return (
        Journey(services(), model)
        .run_query("v", "Coca-Cola Classic", start_node="F0-ENTRANCE")
        .state
    )


def test_an_honest_rewording_passes():
    s = coke_route(good_model(services()))
    assert s["verified"] and s["mismatches"] == [] and s["directions"][0].startswith("Next:")


def test_a_wrong_aisle_is_blocked_and_the_template_shown():
    s = coke_route(describing(lambda line: line.replace("aisle 7", "aisle 8")))
    assert s["verified"] is True and s["mismatches"]
    assert not any("aisle 8" in line for line in s["directions"])
    assert any("aisle 7" in line for line in s["directions"])


def test_a_wrong_distance_is_blocked():
    s = coke_route(describing(lambda line: line.replace(" m.", "0 m.")))
    assert s["mismatches"] and not any(line.startswith("Next:") for line in s["directions"])


def test_a_dropped_shelf_is_blocked():
    s = coke_route(describing(lambda line: line.replace(", shelf 2", "")))
    assert s["mismatches"] and any("shelf 2" in line for line in s["directions"])


def test_stairs_for_a_lift_is_blocked():
    def stairs(line):
        return line.replace("lift", "stairs")

    j = Journey(services(), describing(stairs))
    s = j.run_query("v2", "Everyday Shampoo", start_node="F0-ENTRANCE", step_free=True).state
    assert s["mismatches"] and not any("stairs" in line for line in s["directions"])


def test_a_corrupted_availability_statement_in_state_is_blocked():
    verify = make_verify(services())
    s = coke_route(good_model(services()))
    corrupt = {
        **s,
        "results": [
            r.replace("In stock", "Sold out at this store right now") for r in s["results"]
        ],
    }
    out = verify(corrupt)
    assert out["mismatches"] and out["results"] == s["results"]


def test_a_corrupted_route_distance_in_state_is_blocked():
    verify = make_verify(services())
    s = coke_route(good_model(services()))
    corrupt = {**s, "route": {**s["route"], "distance_m": s["route"]["distance_m"] + 40}}
    out = verify(corrupt)
    assert out["mismatches"] and out["route"] is None
    assert "could not confirm" in " ".join(out["directions"])


def test_a_stop_at_a_place_the_product_is_not_is_blocked():
    verify = make_verify(services())
    s = coke_route(good_model(services()))
    route = s["route"]
    corrupt = {**s, "route": {**route, "stops": [{**route["stops"][0], "node_id": "F1-A06-R03"}]}}
    out = verify(corrupt)
    assert out["mismatches"] and out["route"] is None
