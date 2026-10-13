"""Alternatives that are safe (AC-17) and dietary claims that are never invented (AC-25)."""

import json
import re
from functools import cache
from pathlib import Path

import pytest

from graph.journey import Journey
from graph.model import FakeModel, NoModel, good_model
from graph.nodes.substitutes import safe_candidates
from graph.services import Services
from models.domain import Availability
from services.catalogue import dietary_compatible
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"
DIETARY = {
    "gluten free": "diet_gluten_free",
    "vegan": "diet_vegan",
    "vegetarian": "diet_vegetarian",
    "halal": "diet_halal",
    "nut free": None,  # no recorded attribute — may never be claimed
}


@cache
def services():
    return Services.from_store(load_store(DEMO))


def sku(name):
    return next(p.sku for p in services().store.products.values() if p.name == name)


def run(query, model=None, thread="t"):
    j = Journey(services(), model or good_model(services()))
    out = j.run_query(thread, query, start_node="F0-ENTRANCE")
    while out.pending:
        out = j.resume(
            thread, {q["index"]: q["options"][0]["sku"] for q in out.pending["questions"]}
        )
    return out.state


class TestSafeAlternatives:
    """AC-17, FR-09 — offered alternatives are in stock, in the category, and diet-safe."""

    @pytest.mark.parametrize("model", [good_model(), NoModel()], ids=["model", "no-model"])
    def test_diet_coke_gets_a_matching_in_stock_alternative(self, model):
        s = run("Diet Coke", model)
        diet_coke = sku("Diet Coke")
        offered = s["substitutes"][diet_coke]
        assert offered, "at least one alternative"
        original = services().catalogue.by_sku(diet_coke)
        for alt in offered:
            p = services().catalogue.by_sku(alt)
            assert services().stock.availability(alt) is Availability.IN_STOCK
            assert p.aisle_category == original.aisle_category
            assert dietary_compatible(p, original)

    def test_gluten_free_bread_says_there_is_no_safe_alternative(self):
        s = run("Gluten Free White Bread")
        assert s["substitutes"][sku("Gluten Free White Bread")] == []
        assert "No in-stock alternative matches its recorded dietary needs." in " ".join(
            s["results"]
        )

    def test_every_unavailable_product_in_the_store_gets_only_safe_alternatives(self):
        svc = services()
        unavailable = [
            k for k in svc.store.products if svc.stock.availability(k) is not Availability.IN_STOCK
        ]
        assert len(unavailable) >= 5
        for k in unavailable:
            original = svc.catalogue.by_sku(k)
            for alt in safe_candidates(svc, k):
                p = svc.catalogue.by_sku(alt)
                assert svc.stock.availability(alt) is Availability.IN_STOCK
                assert p.aisle_category == original.aisle_category
                assert dietary_compatible(p, original)

    def test_unknown_never_counts_as_compatible(self):
        svc = services()
        gf_bread = svc.catalogue.by_sku(sku("Gluten Free White Bread"))
        unknown = [p for p in svc.store.products.values() if p.diet_gluten_free is None]
        assert unknown and not any(dietary_compatible(p, gf_bread) for p in unknown)


# ── AC-25: every dietary mention, in every response, is backed by a recorded `true` ───────────


def dietary_mentions_are_backed(lines: list[str]) -> list[str]:
    """Return every mention that is not backed by the data."""
    svc, bad = services(), []
    for line in lines:
        low = line.lower()
        for phrase, field in DIETARY.items():
            for m in re.finditer(rf"\b{phrase}\b", low):
                named = [p for p in svc.store.products.values() if p.name.lower() in low]
                if field and any(
                    phrase in p.name.lower() and getattr(p, field) is True for p in named
                ):
                    continue  # the phrase is part of a product name that truly has it
                status = re.match(r":\s*(yes|no|not recorded)", low[m.end() :])
                if field and status and named:
                    want = {"yes": True, "no": False, "not recorded": None}[status.group(1)]
                    if any(getattr(p, field) is want for p in named):
                        continue  # an explicit status line, matching the record
                bad.append(line)
    return bad


QUERIES = [
    "Gluten Free White Bread",
    "Gluten Free Penne",
    "Halal Chicken Thighs",
    "Coca-Cola Classic",
    "Diet Coke",
    "milk, bread, eggs",
    "something gluten free for my lunch please",
    "I need something vegan for dinner tonight",
]


def dietary_model():
    """A model that asks for dietary filters the shopper stated."""
    good = good_model()

    def understand(schema, system, user):
        text = json.loads(user)["query"].lower()
        wanted = [d for d in ("gluten_free", "vegan", "halal") if d.replace("_", " ") in text]
        return {"items": ["bread"] if "lunch" in text else ["pasta"], "department": [],
                "aisle_category": [], "dietary_required": wanted, "exclude_allergens": []}  # fmt: skip

    return FakeModel(understand=understand, substitute=good.handlers["substitute"],
                     describe=good.handlers["describe"])  # fmt: skip


@pytest.mark.parametrize("model", [dietary_model(), NoModel()], ids=["model", "no-model"])
@pytest.mark.parametrize("query", QUERIES)
def test_ac_25_nfr_03_no_response_invents_a_dietary_claim(query, model):
    s = run(query, model, thread=f"d-{query}")
    assert dietary_mentions_are_backed(s["results"] + s["directions"]) == []


def test_ac_25_a_rewording_that_adds_a_dietary_claim_is_blocked():
    good = good_model()

    def boast(schema, system, user):
        lines = json.loads(user)["lines"]
        return {"lines": [f"{line} Lovely and vegan!" for line in lines]}

    model = FakeModel(understand=good.handlers["understand"], substitute=good.handlers["substitute"],
                      describe=boast)  # fmt: skip
    s = run("Coca-Cola Classic", model, thread="boast")
    assert s["mismatches"] and not any("vegan" in line.lower() for line in s["directions"])


def test_ac_25_asked_for_dietary_status_reads_yes_no_or_not_recorded():
    s = run("something gluten free for my lunch please", dietary_model(), thread="status")
    statements = [r for r in s["results"] if "Gluten free:" in r]
    assert statements, s["results"]
    assert all(re.search(r"Gluten free: (yes|no|not recorded)\.", r) for r in statements)


def test_ac_25_every_product_named_after_a_diet_really_has_it():
    for p in services().store.products.values():
        for phrase, field in DIETARY.items():
            if phrase in p.name.lower():
                assert field and getattr(p, field) is True, p.name
