"""The conditional edges (lld.md §6, as amended in Phase 5)."""

from langgraph.graph import END

from config import MAX_CLARIFY_ROUNDS
from graph.nodes.clarify import ambiguous


def after_start(s) -> str:
    return "resolve_locations" if s.get("action") == "plan" else "classify_query"


def after_classify(s) -> str:
    if s["shape"] in ("too_short", "digits", "bad_barcode"):
        return END  # EC-01, EC-10, EC-52 — nothing claimed
    if s["shape"] == "nl":
        return "understand_query"
    return "resolve_items"


def after_resolve(s) -> str:
    if ambiguous(s) and s.get("clarify_rounds", 0) < MAX_CLARIFY_ROUNDS:
        return "clarify"  # EC-05
    return "check_availability"


def after_availability(s) -> str:
    unavailable = [k for k, v in s["availability"].items() if v != "in_stock"]
    return "suggest_substitutes" if unavailable else "resolve_locations"


def after_locations(s) -> str:
    routable = [b for b in s["basket"] if b["routable"]]
    if not routable:
        return "verify"  # results only — still checked (EC-15)
    if len(routable) == 1 or s.get("mode") == "single":
        return "route_single"  # EC-28
    return "route_multi"
