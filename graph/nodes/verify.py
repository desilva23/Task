"""verify — the gate between a composed answer and the page (lld.md §9, NFR-02, EC-47).

Every fact is derived afresh from the services and compared with what is about to be shown:

1. every SKU in the answer was resolved, or is in the basket being routed;
2. floor, aisle, rack and shelf equal the planogram (via the result statements);
3. availability wording equals the stock position, and no unavailable item has a stop;
4. the route is walkable, its distance equals its hops, its stops are where the products are,
   and a multi-stop route ends at a till;
5. every line of directions makes exactly the claims of the fact line it rewords — the same
   numbers, the same lift or stairs, the same dietary words (AC-25).

A mismatch discards the composed text and shows the template built from the services — never a
patched version of the wrong text — and is recorded.
"""

from config import ROUND_TOLERANCE_M
from graph.nodes.common import subjects
from graph.nodes.substitutes import safe_candidates
from graph.templates import COULD_NOT_CONFIRM, claims, compose_results, directions
from models.domain import Availability


def _route_faults(services, s: dict) -> list[str]:
    route = s.get("route")
    if not route or route["kind"] == "none":
        return []
    engine, nodes, faults = services.engine, route["nodes"], []
    allowed = set(subjects(s))
    hops = [
        engine.graph.edge(a, b, route["step_free"]) for a, b in zip(nodes, nodes[1:], strict=False)
    ]
    if None in hops:
        return ["the route crosses a gap the store map has no path for"]
    walked = sum(h.weight_m + h.penalty_m for h in hops)
    if abs(walked - route["distance_m"]) > ROUND_TOLERANCE_M:
        faults.append(f"distance {route['distance_m']:.1f} m, but the path walks {walked:.1f} m")
    if len(route["stop_at"]) != len(route["stops"]):
        faults.append("stops and their positions disagree")
    for at, stop in zip(route["stop_at"], route["stops"], strict=False):
        if stop["sku"] not in allowed:  # check 1
            faults.append(f"{stop['sku']} was never asked for")
        if services.stock.availability(stop["sku"]) is not Availability.IN_STOCK:  # check 3
            faults.append(f"{stop['sku']} is not in stock but has a stop")
        if stop["node_id"] not in {p.node_id for p in services.planogram.for_sku(stop["sku"])}:
            faults.append(f"{stop['sku']} is not kept at {stop['node_id']}")  # check 2
        if not 0 <= at < len(nodes) or nodes[at] != stop["node_id"]:
            faults.append(f"the path does not pass {stop['node_id']} where it says")
    if route["till"] and (nodes[-1] != route["till"]
                          or services.store.nodes[route["till"]].node_type != "till"):  # fmt: skip
        faults.append("the route does not end at a till")
    return faults


def make_verify(services, model=None):
    def verify(s):
        mismatches = []
        out = {"route": s.get("route"), "directions": list(s.get("directions") or [])}

        # substitutes must still be safe, in stock and in the original's category
        substitutes = {}
        for sku, alts in (s.get("substitutes") or {}).items():
            safe = set(safe_candidates(services, sku))
            substitutes[sku] = [a for a in alts if a in safe]
            if substitutes[sku] != alts:
                mismatches.append(
                    {"check": "substitutes", "claim": alts, "expected": substitutes[sku]}
                )
        fresh_state = {**s, "substitutes": substitutes}

        # checks 1–3: statements and availability, rebuilt from the services
        fresh = compose_results(services, fresh_state, subjects(s))
        if list(s.get("results") or []) != fresh:
            mismatches.append({"check": "statements", "claim": s.get("results"), "expected": fresh})
        stated = s.get("availability") or {}
        actual = {k: services.stock.availability(k).value for k in stated}
        if stated != actual:
            mismatches.append({"check": "availability", "claim": stated, "expected": actual})

        # check 4: the route itself
        faults = _route_faults(services, s)
        if faults:
            mismatches.append({"check": "route", "claim": faults, "expected": "a walkable route"})
            out["route"], out["directions"] = None, [COULD_NOT_CONFIRM]
        else:
            # check 5: each line of directions against the fact line it rewords
            template = directions(services, s.get("route"))
            shown = out["directions"]
            if len(shown) != len(template) or any(
                claims(a) != claims(b) for a, b in zip(shown, template, strict=False)
            ):
                mismatches.append({"check": "directions", "claim": shown, "expected": template})
                out["directions"] = template

        return {
            **out,
            "results": fresh,
            "substitutes": substitutes,
            "availability": {**stated, **actual},
            "mismatches": mismatches,
            "verified": True,  # what is now shown was built from, or checked against, the services
        }

    return verify
