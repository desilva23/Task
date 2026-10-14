"""AC-12, NFR-05 — measured over repeated runs: one product inside 5 s, ten inside 10 s.

Timed end to end through the graph — search, clarification, availability, locations, route,
directions and verify — on both stores. The model here is the in-process fake; the live
GroqCloud timing is in tests/live (run on demand), because CI has no key.
"""

import statistics
import time
from functools import cache
from pathlib import Path

import pytest

from graph.journey import Journey
from graph.model import good_model
from graph.services import Services
from validation import load_store

DATA = Path(__file__).resolve().parents[2] / "data"
RUNS = 20
TEN = ["Bananas", "Carrots", "Whole Milk", "Baked Beans", "Fusilli", "Coca-Cola Classic",
       "Everyday Shampoo", "Toilet Tissue", "Dental Floss", "Salmon Fillet"]  # fmt: skip


@cache
def services(store_id):
    return Services.from_store(load_store(DATA / store_id))


def timed(fn) -> list[float]:
    out = []
    for i in range(RUNS):
        started = time.perf_counter()
        fn(i)
        out.append(time.perf_counter() - started)
    return out


@pytest.mark.parametrize("store_id", ["SBY-DEMO-001", "SBY-PORT-002"])
def test_ac_12_one_product_and_ten_products_inside_budget(store_id):
    svc = services(store_id)
    j = Journey(svc, good_model(svc))

    def one(i):
        assert j.run_query(f"one-{i}", "Coca-Cola Classic").state["verified"]

    def ten(i):
        out = j.run_query(f"ten-{i}", ", ".join(TEN))
        while out.pending:
            out = j.resume(
                f"ten-{i}", {q["index"]: q["options"][0]["sku"] for q in out.pending["questions"]}
            )
        skus = list(dict.fromkeys(out.state["resolved"].values()))
        assert j.plan_route(f"ten-r-{i}", skus).state["verified"]

    one_t, ten_t = timed(one), timed(ten)
    print(f"\n  {store_id}: one product median {statistics.median(one_t) * 1000:.0f} ms, "
          f"worst {max(one_t) * 1000:.0f} ms · ten products median "
          f"{statistics.median(ten_t) * 1000:.0f} ms, worst {max(ten_t) * 1000:.0f} ms")  # fmt: skip
    assert max(one_t) < 5.0 and max(ten_t) < 10.0
