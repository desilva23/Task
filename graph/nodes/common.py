"""Shared helpers for the nodes."""

from models.domain import Availability


def degrade(s: dict, node: str) -> list[str]:
    return list(s.get("degraded") or []) + ([node] if node not in (s.get("degraded") or []) else [])


def subjects(s: dict) -> list[str]:
    """The SKUs a run's statements are about: the basket when planning, else what resolved."""
    if s.get("action") == "plan":
        return list(dict.fromkeys(b["sku"] for b in s.get("basket") or []))
    return list(dict.fromkeys((s.get("resolved") or {}).values()))


def not_in_stock(services, sku: str) -> bool:
    return services.stock.availability(sku) is not Availability.IN_STOCK


def start_or_entrance(services, s: dict) -> tuple[str, list[str]]:
    start = s.get("start_node")
    if start in services.engine.graph.index:
        return start, []
    entrance = services.engine.graph.entrance
    return entrance, [f"Unknown start point {start!r}; started from the entrance instead."]
