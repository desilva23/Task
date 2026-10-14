from pathlib import Path

import pytest

from models.domain import Availability
from services.catalogue import Catalogue
from services.planogram import Planogram
from services.stock import AVAILABILITY_TEXT, Stock
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"
COKE = "7123456"


@pytest.fixture(scope="module")
def demo():
    return load_store(DEMO)


def sku_named(demo, name):
    (sku,) = [p.sku for p in demo.products.values() if p.name == name]
    return sku


def test_ac_01_fr_07_fr_10_a_known_product_is_in_stock_at_floor_aisle_rack_shelf(demo):
    assert Stock(demo).availability(COKE) is Availability.IN_STOCK
    home = next(loc for loc in Planogram(demo).locations(COKE) if loc.location_type == "HOME")
    assert (home.level, home.floor_name, home.aisle, home.rack, home.shelf_no) == (
        1,
        "Food Cupboard & Drinks",
        7,
        3,
        2,
    )
    assert home.needs_colleague is False


def test_ac_20_fr_08_not_sold_here_and_sold_out_differ_in_state_and_wording(demo):
    stock = Stock(demo)
    pepsi = stock.availability(sku_named(demo, "Pepsi Max Cola"))
    diet_coke = stock.availability(sku_named(demo, "Diet Coke"))
    assert (pepsi, diet_coke) == (Availability.NOT_RANGED, Availability.SOLD_OUT)
    assert AVAILABILITY_TEXT[pepsi] != AVAILABILITY_TEXT[diet_coke]


def test_every_availability_state_has_its_own_sentence():
    """FR-08 — the four states read differently."""
    assert set(AVAILABILITY_TEXT) == set(Availability)
    assert len(set(AVAILABILITY_TEXT.values())) == len(Availability)


def test_ec_18_a_sku_with_no_stock_position_is_unknown_not_guessed(demo):
    assert Stock(demo).availability("9999999") is Availability.UNKNOWN


def test_ac_21_fr_11_a_product_in_two_places_reports_both(demo):
    places = {(loc.node_id, loc.location_type) for loc in Planogram(demo).locations(COKE)}
    assert places == {("F1-A07-R03", "HOME"), ("F1-A07-N", "PROMO_ENDCAP")}
    end_cap = next(
        loc for loc in Planogram(demo).locations(COKE) if loc.location_type == "PROMO_ENDCAP"
    )
    assert (end_cap.aisle, end_cap.rack, end_cap.shelf_no) == (7, None, None)


@pytest.mark.parametrize(
    "name, node, kind",
    [("Salmon Fillet", "F0-CTR-02", "COUNTER"), ("London Dry Gin", "F1-CAB-01", "ASSISTED")],
)
def test_ac_16_fr_12_ec_22_ec_23_counters_and_cabinets_have_no_shelf_and_need_a_colleague(
    demo, name, node, kind
):
    (loc,) = Planogram(demo).locations(sku_named(demo, name))
    assert (loc.node_id, loc.location_type, loc.shelf_no, loc.needs_colleague) == (
        node,
        kind,
        None,
        True,
    )


def test_ec_19_a_product_with_no_placement_has_no_location(demo):
    lime = sku_named(demo, "Sparkling Water Lime")
    assert Planogram(demo).locations(lime) == []
    assert Stock(demo).availability(lime) is Availability.IN_STOCK


def test_fr_07_lookups_are_batched_list_in_map_out(demo):
    skus = [COKE, sku_named(demo, "Diet Coke"), "9999999"]
    positions = Stock(demo).positions(skus)
    assert set(positions) == {COKE, skus[1]}
    assert set(Planogram(demo).for_skus(skus)) == set(skus)
    assert Planogram(demo).for_skus(skus)["9999999"] == []


def test_fr_09_by_category_lists_the_category(demo):
    cats = {p.aisle_category for p in Catalogue(demo).by_category("Soft Drinks")}
    assert cats == {"Soft Drinks"}
    assert Catalogue(demo).by_sku(COKE).name == "Coca-Cola Classic"
    assert Catalogue(demo).by_sku("9999999") is None
