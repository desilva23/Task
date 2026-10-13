import dataclasses
import time
from functools import cache
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from models.domain import MultiRoute, NoRoute
from services.basket import Basket, assess
from services.catalogue import Catalogue
from services.multistop import nn_then_2opt, route_multi
from services.planogram import Planogram
from services.routing import RouteEngine
from services.stock import Stock
from services.storegraph import StoreGraph
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def demo():
    store = load_store(DEMO)
    return store, RouteEngine(StoreGraph(store))


def sku(name, size=None):
    store, _ = demo()
    return next(p.sku for p in store.products.values() if p.name == name and size in (None, p.size))


def plan(basket, start="F0-ENTRANCE", step_free=False, store=None, engine=None):
    if store is None:
        store, engine = demo()
    items = assess(basket, Catalogue(store), Stock(store), Planogram(store), engine.graph)
    return items, route_multi(engine, Planogram(store), items, start, step_free)


def stop_levels(route):
    return [s.level for s in route.stops]


def is_till(node_id):
    store, _ = demo()
    return store.nodes[node_id].node_type == "till"


def test_ac_05_fr_17_fr_18_ec_27_three_floors_highest_first_ending_at_a_till():
    basket = Basket().add(
        sku("Everyday Shampoo"),  # F2
        sku("Baked Beans"),  # F1
        sku("Bananas"),  # F0
        sku("Toilet Tissue"),  # F2
        sku("Coca-Cola Classic"),  # F1
    )
    _, route = plan(basket)
    assert isinstance(route, MultiRoute)
    assert stop_levels(route) == sorted(stop_levels(route), reverse=True) == [2, 2, 1, 1, 0]
    assert route.nodes[0] == "F0-ENTRANCE" and route.nodes[-1] == route.till
    assert is_till(route.till)


def test_fr_16_the_route_distance_is_the_sum_of_its_hops():
    _, engine = demo()
    _, route = plan(Basket().add(sku("Everyday Shampoo"), sku("Bananas"), sku("Fusilli")))
    hops = engine.hops(list(route.nodes))
    assert route.distance_m == pytest.approx(sum(h.weight_m + h.penalty_m for h in hops))


def test_ac_23_fr_23_items_from_three_separate_additions_are_all_routed():
    basket = Basket().add(sku("Carrots"))
    basket = basket.add(sku("Porridge Oats"), sku("Carrots"))  # a repeat is not doubled
    basket = basket.add(sku("Dental Floss"))
    assert len(basket.skus) == 3
    _, route = plan(basket)
    assert sorted(s.sku for s in route.stops) == sorted(basket.skus)


def test_ac_24_fr_24_ec_46_a_sold_out_item_stays_in_the_basket_but_out_of_the_route():
    diet_coke = sku("Diet Coke")
    items, route = plan(Basket().add(sku("Bananas")).add(diet_coke))
    (flagged,) = [i for i in items if i.sku == diet_coke]
    assert flagged.routable is False and flagged.reason == "sold_out"
    assert diet_coke not in {s.sku for s in route.stops}
    (excluded,) = route.excluded
    assert excluded.sku == diet_coke and "Diet Coke" in excluded.message
    assert "left out of the route" in excluded.message


def test_ec_17_routability_is_rechecked_on_every_call():
    store, engine = demo()
    beans = sku("Baked Beans")
    basket = Basket().add(beans)
    assert plan(basket)[0][0].routable
    sold_out = dataclasses.replace(
        store, stock={**store.stock, beans: dataclasses.replace(store.stock[beans], shelf_qty=0)}
    )
    items, route = plan(basket, store=sold_out, engine=engine)
    assert items[0].routable is False
    assert isinstance(route, NoRoute) and route.reason == "nothing_routable"


def test_ec_26_one_floor_basket_from_that_floor_never_changes_floor():
    _, route = plan(Basket().add(sku("Bananas"), sku("Carrots"), sku("Mature Cheddar")))
    store, _ = demo()
    assert {store.nodes[n].level for n in route.nodes} == {0}
    assert route.floors == (0,)


def test_ec_33_chilled_items_are_picked_last_in_their_floor_pass():
    basket = Basket().add(sku("Whole Milk"), sku("Bananas"), sku("Carrots"), sku("Crumpets"))
    _, route = plan(basket)
    chilled = [s.placement.location_type == "CHILLER" for s in route.stops]
    assert chilled == [False, False, False, True]


def test_ec_20_a_second_placement_never_adds_a_floor():
    # Coca-Cola sits only on F1 (home and end cap); with F1 already visited, either is fine,
    # but the stop must be on F1 and the basket must not gain a floor
    _, route = plan(Basket().add(sku("Coca-Cola Classic"), sku("Baked Beans")))
    assert set(stop_levels(route)) == {1}


def test_fr_19_step_free_multi_stop_uses_no_stairs():
    _, engine = demo()
    _, route = plan(Basket().add(sku("Everyday Shampoo"), sku("Bananas")), step_free=True)
    hops = engine.hops(list(route.nodes), step_free=True)
    assert all(h.step_free for h in hops)
    assert "stairs" not in {h.kind for h in hops}


def test_ec_31_a_stop_with_no_step_free_path_is_excluded_and_stated():
    store, engine = demo()
    upper_lifts = [e.edge_id for e in store.edges if e.kind == "lift" and e.from_node[:3] == "F1-"]
    closed = engine.closed(upper_lifts)
    _, route = plan(
        Basket().add(sku("Everyday Shampoo"), sku("Bananas")),
        step_free=True,
        store=store,
        engine=closed,
    )
    assert [s.sku for s in route.stops] == [sku("Bananas")]
    (excluded,) = route.excluded
    assert excluded.reason == "no_step_free_route" and "step-free" in excluded.message


def test_fr_17_open_2opt_never_lengthens_nearest_neighbour():
    store, engine = demo()
    placed = Planogram(store).for_skus(list(store.products)[:40]).values()
    stops = [placements[0] for placements in placed if placements]
    floor0 = [p for p in stops if store.nodes[p.node_id].level == 0][:12]

    def length(entry, seq):
        nodes = [entry] + [p.node_id for p in seq]
        return sum(engine.distance(a, b) for a, b in zip(nodes, nodes[1:], strict=False))

    nn_only = nn_then_2opt(engine, "F0-ENTRANCE", floor0, False, improve=False)
    improved = nn_then_2opt(engine, "F0-ENTRANCE", floor0, False)
    assert length("F0-ENTRANCE", improved) <= length("F0-ENTRANCE", nn_only) + 1e-9
    assert sorted(p.node_id for p in improved) == sorted(p.node_id for p in floor0)


def test_fr_16_thirty_items_route_quickly():
    store, _ = demo()
    in_stock = [s for s, pos in store.stock.items() if pos.ranged and pos.shelf_qty > 0][:30]
    started = time.perf_counter()
    _, route = plan(Basket().add(*in_stock))
    assert time.perf_counter() - started < 0.1
    assert isinstance(route, MultiRoute)


@cache
def routable_skus():
    store, engine = demo()
    items = assess(
        Basket().add(*store.products),
        Catalogue(store),
        Stock(store),
        Planogram(store),
        engine.graph,
    )
    return [i.sku for i in items if i.routable]


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_ac_05_fr_16_fr_17_fr_18_invariants_hold_for_random_baskets(data):
    store, engine = demo()
    skus = data.draw(
        st.lists(st.sampled_from(routable_skus()), min_size=1, max_size=12, unique=True)
    )
    start = data.draw(st.sampled_from(sorted(engine.graph.index)))
    step_free = data.draw(st.booleans())
    _, route = plan(Basket().add(*skus), start=start, step_free=step_free)
    assert isinstance(route, MultiRoute)
    assert sorted(s.sku for s in route.stops) == sorted(skus)  # each visited exactly once
    levels = stop_levels(route)
    assert levels == sorted(levels, reverse=True)  # one pass per floor, highest first
    assert route.nodes[0] == start and is_till(route.nodes[-1])
    hops = engine.hops(list(route.nodes), step_free)
    assert route.distance_m == pytest.approx(sum(h.weight_m + h.penalty_m for h in hops))
    if step_free:
        assert all(h.step_free for h in hops)
