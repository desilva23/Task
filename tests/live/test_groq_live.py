"""C-06, NFR-04, NFR-05 — the real GroqCloud, on demand only (`uv run pytest -m live`).

Deselected by default and never run in CI, which has no key. Without a key these fail loudly
rather than skip, so a "passed" here always means the real model was called.
"""

import time
from functools import cache
from pathlib import Path

import pytest

from graph.groq_client import GroqClient
from graph.journey import Journey
from graph.model import NoModel
from graph.model_factory import api_key
from graph.nodes.substitutes import safe_candidates
from graph.prompts import UNDERSTAND
from graph.services import Services
from models.llm import ParsedQuery
from validation import load_store

pytestmark = pytest.mark.live
DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def services():
    return Services.from_store(load_store(DEMO))


def groq():
    key = api_key()
    assert key, "no GROQ_API_KEY — add it to .streamlit/secrets.toml (never to the repo)"
    return GroqClient(key)


def test_c_06_understand_returns_a_strictly_valid_parse():
    raw = groq().complete(
        "understand", ParsedQuery, UNDERSTAND, '{"query": "something for a headache"}'
    )
    parsed = ParsedQuery.model_validate(raw)
    assert parsed.items, raw


def test_nfr_05_one_product_journey_verified_within_five_seconds():
    j = Journey(services(), groq())
    started = time.perf_counter()
    s = j.run_query("live-1", "Coca-Cola Classic", start_node="F0-ENTRANCE").state
    elapsed = time.perf_counter() - started
    assert s["verified"] and elapsed < 5, (elapsed, s["degraded"])
    assert "describe_route" not in s["degraded"], "the live model should have described the route"
    baseline = Journey(services(), NoModel()).run_query("base", "Coca-Cola Classic").state
    assert s["route"]["nodes"] == baseline["route"]["nodes"]  # the model never moves a fact
    print(f"\n  {elapsed:.2f}s · mismatches={len(s['mismatches'])}")
    for line in s["directions"]:
        print("   ", line)


def test_fr_09_live_substitutes_are_chosen_from_the_safe_list():
    s = Journey(services(), groq()).run_query("live-2", "Diet Coke").state
    diet_coke = next(p.sku for p in services().store.products.values() if p.name == "Diet Coke")
    assert "suggest_substitutes" not in s["degraded"]
    assert set(s["substitutes"][diet_coke]) <= set(safe_candidates(services(), diet_coke))


def test_fr_04_a_sentence_reaches_real_products():
    j = Journey(services(), groq())
    out = j.run_query("live-3", "I need something for a headache please", start_node="F0-ENTRANCE")
    assert "understand_query" not in out.state["degraded"]
    real = set(services().store.products)
    cands = [k for row in out.state["candidates"] for k in row]
    assert cands and set(cands) <= real
    categories = {services().catalogue.by_sku(k).aisle_category for k in cands}
    print(f"\n  categories offered: {sorted(categories)}")


def test_ac_12_live_one_product_and_ten_products_inside_budget():
    """Three runs each with GroqCloud — kept small for the free tier's 8,000 tokens a minute."""
    names = ["Bananas", "Carrots", "Whole Milk", "Baked Beans", "Fusilli", "Coca-Cola Classic",
             "Everyday Shampoo", "Toilet Tissue", "Dental Floss", "Salmon Fillet"]  # fmt: skip
    j = Journey(services(), groq())
    one, ten = [], []
    for i in range(3):
        t = time.perf_counter()
        j.run_query(f"p1-{i}", "Coca-Cola Classic")
        one.append(time.perf_counter() - t)
        t = time.perf_counter()
        out = j.run_query(f"p10-{i}", ", ".join(names))
        while out.pending:
            out = j.resume(
                f"p10-{i}", {q["index"]: q["options"][0]["sku"] for q in out.pending["questions"]}
            )
        j.plan_route(f"p10r-{i}", list(dict.fromkeys(out.state["resolved"].values())))
        ten.append(time.perf_counter() - t)
    print(
        f"\n  live: one product {[round(x, 2) for x in one]} s · ten {[round(x, 2) for x in ten]} s"
    )
    assert max(one) < 5 and max(ten) < 10
