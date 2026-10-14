"""The page's logic, tested without a browser: routes drawn twice (AC-22) and directions that
stand on their own as text (AC-27)."""

import json
import re
from functools import cache
from pathlib import Path

import pytest

from graph.journey import Journey
from graph.model import FakeModel, NoModel, good_model
from graph.services import Services
from present.floorplate import floor_plates
from present.view import addable, group_results, start_options
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def services():
    return Services.from_store(load_store(DEMO))


def sku(name):
    return next(p.sku for p in services().store.products.values() if p.name == name)


def routed(names, step_free=False, model=None):
    j = Journey(services(), model or NoModel())
    return j.plan_route("r", [sku(n) for n in names], "F0-ENTRANCE", step_free).state


THREE_FLOORS = ["Everyday Shampoo", "Baked Beans", "Bananas", "Whole Milk", "Salmon Fillet"]


class TestRouteDrawnTwice:
    """AC-22, FR-20 — the directions and the floor plates describe the same sequence."""

    @pytest.mark.parametrize("names", [["Coca-Cola Classic"], THREE_FLOORS])
    def test_the_plates_trace_exactly_the_route(self, names):
        s = routed(names)
        plates = floor_plates(services(), s["route"])
        segments = sorted((seg.start, seg.nodes) for p in plates for seg in p.segments)
        rebuilt = [n for _, nodes in segments for n in nodes]
        assert rebuilt == s["route"]["nodes"]
        for p in plates:
            for seg in p.segments:
                assert all(services().store.nodes[n].level == p.level for n in seg.nodes)
                assert f'data-route="{" ".join(seg.nodes)}"' in p.svg

    def test_stop_markers_are_numbered_in_directions_order(self):
        s = routed(THREE_FLOORS)
        plates = floor_plates(services(), s["route"])
        markers = sorted((n, node) for p in plates for n, node in p.stops)
        assert [node for _, node in markers] == [st["node_id"] for st in s["route"]["stops"]]
        picked = [line for line in s["directions"] if "pick up" in line]
        for (n, _node), line, stop in zip(markers, picked, s["route"]["stops"], strict=True):
            label = services().catalogue.by_sku(stop["sku"]).name
            assert label in line
            assert f'data-stop="{n}"' in "".join(p.svg for p in plates)

    def test_each_floor_change_has_a_marker_at_both_ends(self):
        s = routed(THREE_FLOORS)
        plates = floor_plates(services(), s["route"])
        nodes, store = s["route"]["nodes"], services().store
        ends = {n for a, b in zip(nodes, nodes[1:], strict=False)
                if store.nodes[a].level != store.nodes[b].level for n in (a, b)}  # fmt: skip
        drawn = {
            seg
            for p in plates
            for seg in re.findall(r'data-transition="[^"]+" data-node="([^"]+)"', p.svg)
        }
        assert drawn == ends


class TestDirectionsAsText:
    """AC-27, NFR-10 — read with the map removed, the list still says everything."""

    @pytest.mark.parametrize("step_free", [False, True])
    @pytest.mark.parametrize("model", [NoModel(), good_model()], ids=["template", "reworded"])
    def test_every_stop_and_every_floor_change_is_named(self, step_free, model):
        s = routed(THREE_FLOORS, step_free, model)
        text = "\n".join(s["directions"]).lower()
        for stop in s["route"]["stops"]:
            node = services().store.nodes[stop["node_id"]]
            placement = next(p for p in services().planogram.for_sku(stop["sku"])
                             if p.node_id == stop["node_id"])  # fmt: skip
            assert f"floor {node.level}" in text
            if node.node_type == "rack":
                assert f"aisle {node.aisle}, rack {node.rack}, shelf {placement.shelf_no}" in text
            else:
                assert "ask a colleague" in text  # a counter or cabinet, with no shelf
        route_nodes = s["route"]["nodes"]
        levels = [services().store.nodes[n].level for n in route_nodes]
        floor_changes = sum(1 for a, b in zip(levels, levels[1:], strict=False) if a != b)
        named_changes = re.findall(r"take the (lift|stairs) (?:up|down) to floor \d", text)
        assert len(named_changes) == floor_changes
        if step_free:
            assert set(named_changes) == {"lift"}  # AC-07: lifts only

    def test_a_rewording_that_drops_a_location_word_is_blocked(self):
        good = good_model()

        def terse(schema, system, user):
            lines = json.loads(user)["lines"]
            return {"lines": [line.replace("aisle ", "") for line in lines]}

        model = FakeModel(understand=good.handlers["understand"], describe=terse)
        s = routed(["Coca-Cola Classic"], model=model)
        assert s["mismatches"] and any("aisle 7" in line for line in s["directions"])


class TestView:
    """FR-15, FR-21, FR-22 — start point, grouping and the basket gate."""

    def test_start_options_default_to_the_entrance_and_cover_every_aisle(self):
        options = start_options(services())
        assert options[0][0][1] == "F0-ENTRANCE"
        aisles = {
            (n.level, n.aisle) for n in services().store.nodes.values() if n.node_type == "rack"
        }
        offered = {(lv, int(label.split()[-1])) for lv, opts in options.items()
                   for label, _ in opts if label.startswith("Aisle")}  # fmt: skip
        assert offered == aisles

    def test_ac_08_available_first_and_one_action_adds_only_those(self):
        j = Journey(services(), NoModel())
        s = j.run_query("g", "bananas, baked beans, dental floss, diet coke").state
        groups = group_results(services(), s)
        assert [r.sku for r in groups.available] == [
            sku("Bananas"),
            sku("Baked Beans"),
            sku("Dental Floss"),
        ]
        assert [r.sku for r in groups.unavailable] == [sku("Diet Coke")]
        assert addable(groups) == [sku("Bananas"), sku("Baked Beans"), sku("Dental Floss")]


def test_fr_20_ac_15_no_label_on_any_plate_touches_another_thing():
    """Owner's report (2026-10-14): words on the map ran into each other. Every product routed
    on its own from two different starts, and baskets over every floor, must place every label
    in clear space — no shelf, box, pin or other label under it, nothing off the edge."""
    from present import floorplate

    floorplate.CROWDED.clear()
    svc = services()
    j = Journey(svc, NoModel())
    ranged = [p.sku for p in svc.catalogue._products.values()
              if svc.stock.availability(p.sku).value == "in_stock"]  # fmt: skip
    for start in ("F0-ENTRANCE", "F1-A07-S"):
        for k in ranged:
            route = j.plan_route(f"r-{start}-{k}", [k], start_node=start).state["route"]
            if route and route["kind"] != "none":
                floor_plates(svc, route)
    for start in ("F0-ENTRANCE", "F2-A05-N"):
        for i in range(0, len(ranged), 8):
            route = j.plan_route(f"b-{start}-{i}", ranged[i : i + 8], start_node=start).state[
                "route"
            ]
            floor_plates(svc, route)
    assert floorplate.CROWDED == []
