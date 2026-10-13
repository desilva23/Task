"""suggest_substitutes — in-stock alternatives that keep the original's recorded dietary needs.

The service filters for safety *before* the model sees anything; the model only picks among
safe options, and a pick outside them is dropped (GroundingError). Fallback: the same safe
list in popularity order.
"""

import json

from errors import GroundingError
from graph import prompts
from graph.nodes.common import degrade, not_in_stock
from models.domain import Availability
from models.llm import SubstituteChoice
from services.catalogue import dietary_compatible

KEEP = 3


def safe_candidates(services, sku: str) -> list[str]:
    original = services.catalogue.by_sku(sku)
    pool = [
        p
        for p in services.catalogue.by_category(original.aisle_category)
        if p.sku != sku
        and services.stock.availability(p.sku) is Availability.IN_STOCK
        and dietary_compatible(p, original)
    ]
    return [p.sku for p in sorted(pool, key=lambda p: (-p.popularity, p.sku))]


def make_suggest_substitutes(services, model):
    def suggest_substitutes(s):
        out, degraded = {}, list(s.get("degraded") or [])
        for sku in s["availability"]:
            if not not_in_stock(services, sku):
                continue
            safe = safe_candidates(services, sku)
            out[sku] = safe[:KEEP]
            if not safe:
                continue  # nothing safe to offer — said so, never an unsafe one (AC-17)
            try:
                original = services.catalogue.by_sku(sku)
                user = json.dumps({
                    "original": {"name": original.name, "size": original.size},
                    "candidates": [
                        {"sku": k, "name": services.catalogue.by_sku(k).name} for k in safe
                    ],
                })  # fmt: skip
                choice = SubstituteChoice.model_validate(
                    model.complete("substitute", SubstituteChoice, prompts.SUBSTITUTE, user)
                )
                if choice.sku not in safe:
                    raise GroundingError(choice.sku)
                out[sku] = [choice.sku] + [k for k in safe if k != choice.sku][: KEEP - 1]
            except Exception:
                degraded = degrade({"degraded": degraded}, "suggest_substitutes")
        return {"substitutes": out, "degraded": degraded}

    return suggest_substitutes
