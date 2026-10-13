"""route_single and route_multi — the route engine, turned into plain-valued state."""

from graph.nodes.common import start_or_entrance
from models.domain import NoRoute
from services.basket import Basket, assess
from services.multistop import route_multi as plan_multi


def _excluded(s: dict) -> list[dict]:
    return [
        {"sku": b["sku"], "reason": b["reason"], "message": b["message"]}
        for b in s["basket"]
        if not b["routable"]
    ]


def _none(r: NoRoute) -> dict:
    return {"kind": "none", "reason": r.reason, "message": r.message}


def make_route_single(services, model):
    def route_single(s):
        start, errors = start_or_entrance(services, s)
        sku = next(b["sku"] for b in s["basket"] if b["routable"])
        try:
            r = services.engine.route_single(start, services.planogram.for_sku(sku), s["step_free"])
        except Exception as exc:  # a data bug after V-70 — surface it, no partial route
            return {"route": None, "errors": [*s.get("errors", []), *errors, str(exc)]}
        if isinstance(r, NoRoute):
            return {"route": _none(r), "start_node": start, "errors": s.get("errors", []) + errors}
        route = {
            "kind": "single",
            "nodes": list(r.nodes),
            "distance_m": r.distance_m,
            "stops": [{"sku": sku, "node_id": r.placement.node_id}],
            "stop_at": [len(r.nodes) - 1],
            "till": None,
            "excluded": _excluded(s),
            "step_free": s["step_free"],
        }
        return {"route": route, "start_node": start, "errors": s.get("errors", []) + errors}

    return route_single


def make_route_multi(services, model):
    def route_multi(s):
        start, errors = start_or_entrance(services, s)
        items = assess(
            Basket(tuple(b["sku"] for b in s["basket"])),
            services.catalogue,
            services.stock,
            services.planogram,
            services.engine.graph,
        )
        try:
            r = plan_multi(services.engine, services.planogram, items, start, s["step_free"])
        except Exception as exc:  # fallback: floor-ordered, without 2-opt (lld.md §6)
            errors.append(f"route optimisation failed ({exc}); used the simple floor order")
            r = plan_multi(
                services.engine, services.planogram, items, start, s["step_free"], improve=False
            )
        if isinstance(r, NoRoute):
            return {"route": _none(r), "start_node": start, "errors": s.get("errors", []) + errors}
        route = {
            "kind": "multi",
            "nodes": list(r.nodes),
            "distance_m": r.distance_m,
            "stops": [{"sku": st.sku, "node_id": st.node_id} for st in r.stops],
            "stop_at": list(r.stop_at),
            "till": r.till,
            "excluded": [
                {"sku": e.sku, "reason": e.reason, "message": e.message} for e in r.excluded
            ],
            "step_free": s["step_free"],
        }
        return {"route": route, "start_node": start, "errors": s.get("errors", []) + errors}

    return route_multi
