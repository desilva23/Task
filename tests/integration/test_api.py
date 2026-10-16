"""The HTTP API the page calls (C-03, hld.md §4.1), driven with FastAPI's test client. The model
is forced off, so these never reach GroqCloud even with a key on the machine."""

import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import index

REPO = Path(__file__).resolve().parents[2]
F0_ENTRANCE = "F0-ENTRANCE"


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("LOCATOR_MODEL", "off")
    return TestClient(index.app, raise_server_exceptions=False)


def search(api, query, answers=(), **where):
    r = api.post("/api/search", json={"query": query, "answers": list(answers),
                                      "start": F0_ENTRANCE, **where})  # fmt: skip
    assert r.status_code == 200, r.text
    return r.json()


def scan(api, code):
    r = api.post("/api/scan", json={"code": code, "start": F0_ENTRANCE})
    assert r.status_code == 200, r.text
    return r.json()


def route(api, skus, **where):
    r = api.post("/api/route", json={"skus": skus, "start": F0_ENTRANCE, **where})
    assert r.status_code == 200, r.text
    return r.json()


def text(view) -> str:
    return json.dumps(view, ensure_ascii=False)


def barcode(name):
    rows = csv.DictReader((REPO / "data/SBY-DEMO-001/products.csv").open())
    return next(r["barcode"] for r in rows if r["name"] == name)


def test_c_04_fr_15_the_store_call_offers_floors_and_aisles_and_no_store_line(api):
    store = api.get("/api/store").json()
    assert store["entrance"] == F0_ENTRANCE
    assert [f["level"] for f in store["floors"]] == [0, 1, 2]
    assert store["floors"][0]["spots"][0] == {"label": "Entrance", "node": F0_ENTRANCE}
    assert "synthetic" not in text(store).lower()  # no data-provenance line on the page (C-04)
    assert store["name"] == "Demo Superstore"  # the switcher names each store (FR-31)


def test_ac_08_fr_21_fr_22_three_available_one_not_one_action_adds_three(api):
    view = search(api, "bananas, baked beans, dental floss, diet coke")
    assert len(view["available"]) == 3 and len(view["unavailable"]) == 1
    assert view["offer_add"] is True and len(view["addable"]) == 3
    assert view["unavailable"][0]["sku"] not in view["addable"]


def test_fr_24_an_unavailable_item_routed_is_left_out_and_said_so(api):
    view = search(api, "bananas, diet coke")
    skus = view["addable"] + [r["sku"] for r in view["unavailable"]]
    planned = route(api, skus)["route"]
    assert planned["directions"] and any("left out of the route" in m for m in planned["excluded"])


def test_fr_05_ec_34_a_question_answered_by_resending_the_search(api, monkeypatch):
    made = []

    class Watched(index.Journey):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            made.append(self)

    monkeypatch.setattr(index, "Journey", Watched)
    first = search(api, "milk")
    question = first["pending"]["questions"][0]
    pick = question["options"][1]["sku"]
    answered = search(api, "milk", answers=[{question["index"]: pick}])
    assert answered["pending"] is None
    assert [r["sku"] for r in answered["available"] + answered["unavailable"]] == [pick]
    assert "pick up" in text(answered["route"])  # a single product routes once chosen
    assert len(made) == 2 and all(not j.checkpointer.storage for j in made)  # nothing kept


def test_ec_05_an_answer_that_was_not_offered_is_asked_again(api):
    view = search(api, "milk", answers=[{"0": "7123456"}])  # Coca-Cola, never an option for milk
    assert view["pending"] is not None


def test_nfr_04_the_view_says_when_the_model_was_not_used(api):
    assert "plain wording" in search(api, "Coca-Cola Classic")["degraded"].lower()


def test_fr_19_step_free_is_one_flag(api):
    view = search(api, "Everyday Shampoo", step_free=True)
    shown = " ".join(view["route"]["directions"]).lower()
    assert "lift" in shown and "stairs" not in shown


def test_ac_22_the_route_comes_with_its_floor_plates(api):
    view = search(api, "Everyday Shampoo")
    plates = view["route"]["plates"]
    assert plates and all(p["svg"].startswith("<svg") for p in plates)


def test_ac_28_ec_48_typed_digits_find_the_product_with_no_choice(api):
    view = scan(api, barcode("Coca-Cola Classic"))
    assert view["pending"] is None and view["available"][0]["label"].startswith("Coca-Cola")
    assert view["addable"] == [view["available"][0]["sku"]] and view["offer_add"] is True


def test_ec_52_bad_digits_say_so(api):
    assert "isn't a valid barcode" in scan(api, "1234567890123")["notice"]


def test_ec_50_a_foreign_barcode_says_so(api):
    assert "not in this store's catalogue" in text(scan(api, "5449000000996"))


def test_ec_10_digits_in_the_search_box_point_to_the_scan(api):
    assert "Scan a barcode" in search(api, barcode("Coca-Cola Classic"))["notice"]


def test_ec_01_a_too_short_search_says_why(api):
    assert "at least two letters" in search(api, "m")["notice"]


def test_ec_17_a_route_is_never_planned_to_an_empty_shelf(api):
    diet = barcode("Diet Coke")
    sold_out = scan(api, diet)["unavailable"][0]["sku"]
    planned = route(api, [sold_out])
    assert planned["route"] is None or planned["route"]["kind"] == "none"


def test_ac_31_fr_28_every_suggestion_searches_straight_to_its_product(api):
    """A suggestion's label is what the box receives, so each one must find exactly that product
    with no question — checked for every product the store sells."""
    products = api.get("/api/store").json()["products"]
    ranged = [r for r in csv.DictReader((REPO / "data/SBY-DEMO-001/stock.csv").open())
              if r["ranged"] == "true"]  # fmt: skip
    assert len(products) == len(ranged) > 100
    for p in products:
        view = search(api, p["label"])
        found = [r["sku"] for r in view["available"] + view["unavailable"]]
        assert view["pending"] is None and found == [p["sku"]], p["label"]
        assert p["in_stock"] == bool(view["available"]), p["label"]  # the mark matches the answer


def test_ec_66_a_product_not_sold_here_is_never_suggested(api):
    products = api.get("/api/store").json()["products"]
    labels = " ".join(p["label"] for p in products)
    assert "Pepsi" not in labels and "Diet Coke" in labels  # not ranged vs sold out
    diet = next(p for p in products if p["label"].startswith("Diet Coke"))
    assert diet["in_stock"] is False and "Diet Coke" in diet["terms"]


def test_ac_32_a_list_without_commas_is_searched_item_by_item_and_says_so(api):
    view = search(api, "milk bread chicken")
    assert view["split"] == [{"from": "milk bread chicken", "into": ["milk", "bread", "chicken"]}]
    assert [q["term"] for q in view["pending"]["questions"]] == ["milk", "bread", "chicken"]
    assert search(api, '"milk bread chicken"')["split"] == []  # the page's "as one item"


def test_ac_36_fr_31_the_store_call_lists_every_store_and_opens_any(api):
    default = api.get("/api/store").json()
    assert default["id"] == "SBY-DEMO-001"
    assert [(s["id"], s["floors"]) for s in default["stores"]] == [
        ("SBY-DEMO-001", 3), ("SBY-CITY-003", 5), ("SBY-PORT-002", 2)
    ]  # fmt: skip
    city = api.get("/api/store", params={"store": "SBY-CITY-003"}).json()
    assert city["name"] == "City Flagship" and [f["level"] for f in city["floors"]] == [
        0,
        1,
        2,
        3,
        4,
    ]


def test_ac_36_the_same_product_is_answered_from_each_store_s_own_data(api):
    where = {}
    for store in ("SBY-DEMO-001", "SBY-CITY-003", "SBY-PORT-002"):
        r = api.post("/api/search", json={"store": store, "query": "everyday shampoo",
                                          "start": F0_ENTRANCE}).json()  # fmt: skip
        where[store] = r["available"][0]["statement"]
    assert len(set(where.values())) == 3, where
    assert "Floor 3" in where["SBY-CITY-003"]


def test_ac_36_a_five_floor_route_clears_the_top_floor_first_and_ends_at_a_till(api):
    skus = []
    for q in ("dry dog food", "everyday shampoo", "bananas"):
        r = api.post("/api/search", json={"store": "SBY-CITY-003", "query": q,
                                          "start": F0_ENTRANCE}).json()  # fmt: skip
        skus += r["addable"]
    r = api.post("/api/route", json={"store": "SBY-CITY-003", "skus": skus,
                                     "start": F0_ENTRANCE}).json()  # fmt: skip
    steps = r["route"]["directions"]
    picks = [s for s in steps if "pick up" in s or "grab" in s]
    assert picks[0].startswith("Floor 4") and picks[-1].startswith("Floor 0"), steps
    assert "checkout" in steps[-2].lower() and {p["level"] for p in r["route"]["plates"]} == {
        0,
        1,
        2,
        3,
        4,
    }


def test_ec_74_an_unknown_store_is_refused_never_answered_from_another(api):
    assert api.get("/api/store", params={"store": "SBY-NOPE-999"}).status_code == 404
    r = api.post(
        "/api/search", json={"store": "SBY-NOPE-999", "query": "milk", "start": F0_ENTRANCE}
    )
    assert r.status_code == 404 and r.json() == {"error": "That store isn't available here."}
