"""FR-03 — a scan through the journey graph: the exact product, the same answer a typed search
gives, and a plain "not ours" for a barcode the catalogue does not have (AC-28)."""

from functools import cache
from pathlib import Path

from graph.journey import Journey
from graph.model import NoModel, good_model
from graph.services import Services
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"
FOREIGN = "5449000000996"  # a valid EAN-13 from outside the synthetic range


@cache
def services():
    return Services.from_store(load_store(DEMO))


def product(name):
    return next(p for p in services().store.products.values() if p.name == name)


class Recording:
    """The well-behaved fake, noting which tasks it was asked to do."""

    def __init__(self):
        self.inner, self.tasks = good_model(services()), []

    def complete(self, task, schema, system, user):
        self.tasks.append(task)
        return self.inner.complete(task, schema, system, user)


def scan(code, model=None, thread="scan-1", **kw):
    j = Journey(services(), model or good_model(services()))
    return j.run_scan(thread, code, start_node="F0-ENTRANCE", **kw)


def test_ac_28_a_scan_returns_that_exact_product_with_no_choice():
    coke = product("Coca-Cola Classic")
    typed = Journey(services(), good_model(services())).run_query("t", "coca-cola")
    assert typed.pending is not None  # by name it is a choice …
    out = scan(coke.barcode)
    s = out.state
    assert out.pending is None  # … by barcode it is not
    assert s["resolved"] == {"0": coke.sku} and s["verified"] is True and not s["mismatches"]
    assert s["availability"] == {coke.sku: "in_stock"}
    assert s["route"]["kind"] == "single" and s["route"]["stops"][0]["sku"] == coke.sku
    assert any(line.startswith("Coca-Cola Classic") for line in s["results"])


def test_ac_28_ec_48_typed_digits_return_the_same_product():
    coke = product("Coca-Cola Classic")
    code = coke.barcode
    out = scan(f"{code[:1]} {code[1:7]} {code[7:]}")
    assert out.state["resolved"] == {"0": coke.sku} and out.state["verified"] is True


def test_ac_28_ec_50_a_barcode_not_in_the_catalogue_says_so():
    s = scan(FOREIGN).state
    assert s["resolved"] == {} and s["verified"] is True and s["route"] is None
    assert s["term_status"] == ["not_catalogued"] and s["candidates"] == [[]]
    line = " ".join(s["results"])
    assert FOREIGN in line and "not in this store's catalogue" in line
    assert "Did you mean" not in line


def test_ec_52_mistyped_digits_are_refused_before_any_lookup():
    code = product("Coca-Cola Classic").barcode
    for typed in (code[:-1] + str((int(code[-1]) + 1) % 10), code[:12], "abc"):
        s = scan(typed).state
        assert s["shape"] == "bad_barcode" and "isn't a valid barcode" in s["message"]
        assert not s.get("resolved") and not s.get("results")


def test_fr_08_ec_04_a_scanned_product_reports_as_a_typed_one_would():
    diet, pepsi = product("Diet Coke"), product("Pepsi Max Cola")
    sold_out = scan(diet.barcode).state
    assert sold_out["availability"] == {diet.sku: "sold_out"} and sold_out["route"] is None
    assert sold_out["substitutes"][diet.sku]
    unranged = scan(pepsi.barcode).state
    assert unranged["availability"] == {pepsi.sku: "not_ranged"}
    assert unranged["not_ranged"] == [pepsi.sku]


def test_fr_03_a_scan_never_asks_the_model_to_understand_it():
    model = Recording()
    scan(product("Coca-Cola Classic").barcode, model=model)
    assert "understand" not in model.tasks and model.tasks == ["describe"]


def test_ac_11_fr_03_a_scan_works_with_every_model_call_failing():
    coke = product("Coca-Cola Classic")
    s = scan(coke.barcode, model=NoModel()).state
    assert s["resolved"] == {"0": coke.sku} and s["verified"] is True
    assert s["route"]["stops"][0]["sku"] == coke.sku


def test_fr_23_fr_03_a_scanned_product_is_routed_from_the_basket():
    coke = product("Coca-Cola Classic")
    j = Journey(services(), good_model(services()))
    j.run_scan("scan", coke.barcode, start_node="F2-A01-N")
    routed = j.plan_route("route", [coke.sku], start_node="F2-A01-N").state
    assert routed["verified"] is True and routed["route"]["stops"][0]["sku"] == coke.sku
