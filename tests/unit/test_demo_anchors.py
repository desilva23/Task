"""C-04 — the synthetic demo store carries a fixed scenario for each later acceptance test.

These prove the data is there, not the behaviour, so they cite C-04 rather than the AC each
scenario serves; the comments name it with a space so the matrix does not count it as proven.
"""

from pathlib import Path

import pytest

from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"
DIET = ("diet_gluten_free", "diet_vegan", "diet_vegetarian", "diet_halal", "allergens_contains")


@pytest.fixture(scope="module")
def demo():
    return load_store(DEMO)


def named(demo, name, size=None):
    (p,) = [p for p in demo.products.values() if p.name == name and size in (None, p.size)]
    return p


def placements(demo, sku):
    return sorted((p for p in demo.placements if p.sku == sku), key=lambda p: p.node_id)


def in_stock(demo, sku):
    s = demo.stock[sku]
    return s.ranged and s.shelf_qty > 0


# scenario for AC 01, AC 21 — proven by its own phase
def test_coca_cola_has_a_home_shelf_and_an_end_cap(demo):
    coke = demo.products["7123456"]
    assert (coke.name, coke.size, demo.stock["7123456"].shelf_qty) == (
        "Coca-Cola Classic",
        "500ml",
        14,
    )
    end_cap, home = placements(demo, "7123456")
    assert (home.node_id, home.location_type, home.shelf_no) == ("F1-A07-R03", "HOME", 2)
    assert (end_cap.node_id, end_cap.location_type, end_cap.shelf_no) == (
        "F1-A07-N",
        "PROMO_ENDCAP",
        None,
    )


# scenario for AC 02 — proven by its own phase
def test_milk_bread_and_eggs_are_in_stock_on_the_ground_floor(demo):
    for term in ("milk", "bread", "eggs"):
        hits = [p for p in demo.products.values() if term in p.synonyms and in_stock(demo, p.sku)]
        assert hits, term
        floors = {demo.nodes[pl.node_id].level for p in hits for pl in placements(demo, p.sku)}
        assert 0 in floors, term


# scenario for AC 03 — proven by its own phase
def test_milk_is_ambiguous(demo):
    assert len([p for p in demo.products.values() if "milk" in p.synonyms]) >= 4


# scenario for AC 05 — proven by its own phase
def test_every_floor_has_in_stock_products(demo):
    floors = {demo.nodes[pl.node_id].level for pl in demo.placements if in_stock(demo, pl.sku)}
    assert floors == {0, 1, 2}


# scenario for AC 16 — proven by its own phase
def test_counter_and_cabinet_products_have_no_shelf(demo):
    kinds = {}
    for pl in demo.placements:
        if pl.location_type in ("COUNTER", "ASSISTED"):
            assert (pl.shelf_no, pl.facing_from, pl.facing_count) == (None, None, None)
            kinds.setdefault(pl.location_type, set()).add(pl.node_id)
    assert kinds == {
        "COUNTER": {"F0-CTR-01", "F0-CTR-02", "F0-CTR-03"},
        "ASSISTED": {"F1-CAB-01", "F2-CAB-01"},
    }


# scenario for AC 17 — proven by its own phase
def test_diet_coke_is_sold_out_with_a_matching_alternative(demo):
    diet_coke = named(demo, "Diet Coke")
    assert demo.stock[diet_coke.sku].ranged and demo.stock[diet_coke.sku].shelf_qty == 0
    zero = named(demo, "Coca-Cola Zero Sugar")
    assert zero.aisle_category == diet_coke.aisle_category and in_stock(demo, zero.sku)
    assert [getattr(zero, a) for a in DIET] == [getattr(diet_coke, a) for a in DIET]


# scenario for AC 17 — proven by its own phase
def test_gluten_free_bread_has_no_gluten_free_alternative(demo):
    gf = named(demo, "Gluten Free White Bread")
    assert gf.diet_gluten_free is True and demo.stock[gf.sku].shelf_qty == 0
    others = [
        p
        for p in demo.products.values()
        if p.aisle_category == gf.aisle_category and p.sku != gf.sku and in_stock(demo, p.sku)
    ]
    assert others and not [p for p in others if p.diet_gluten_free is True]


# scenario for AC 19, AC 20 — proven by its own phase
def test_pepsi_is_not_ranged_and_diet_coke_is_sold_out(demo):
    pepsi = named(demo, "Pepsi Max Cola")
    assert "cola" in pepsi.synonyms
    assert (demo.stock[pepsi.sku].ranged, demo.stock[pepsi.sku].shelf_qty) == (False, 0)
    assert placements(demo, pepsi.sku) == []
    diet_coke = demo.stock[named(demo, "Diet Coke").sku]
    assert (diet_coke.ranged, diet_coke.shelf_qty) == (True, 0)


# scenario for AC 25 — proven by its own phase
def test_some_dietary_attributes_are_unknown(demo):
    assert demo.products["7123456"].diet_halal is None
    assert any(p.allergens_contains is None for p in demo.products.values())


# scenario for EC 19 — proven by its own phase
def test_sparkling_water_lime_is_stocked_with_no_placement(demo):
    lime = named(demo, "Sparkling Water Lime")
    assert in_stock(demo, lime.sku) and placements(demo, lime.sku) == []


# scenario for EC 24 — proven by its own phase
def test_a_seasonal_product_is_sold_out(demo):
    seasonal = {pl.sku for pl in demo.placements if pl.seasonal}
    assert any(demo.stock[s].shelf_qty == 0 for s in seasonal)


# scenario for EC 33 — proven by its own phase
def test_chilled_products_sit_in_chillers(demo):
    milk = named(demo, "Whole Milk")
    assert {pl.location_type for pl in placements(demo, milk.sku)} == {"CHILLER"}


def test_c_04_a_04_the_demo_store_is_synthetic_and_sized_as_assumed(demo):
    assert demo.info.data_provenance == "synthetic"
    assert 150 <= len(demo.products) <= 200


def test_a_03_the_demo_store_has_three_floors(demo):
    assert {n.level for n in demo.nodes.values()} == {0, 1, 2}
