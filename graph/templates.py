"""The deterministic wording — result statements and route directions — built from the
services alone. This is what a shopper sees when the model is off, what the model rewords when
it is on, and what ``verify`` rebuilds to check either. No dietary property is ever stated.
"""

import re

from models.domain import Availability
from services.stock import AVAILABILITY_TEXT

VERTICAL = ("lift", "stairs", "escalator")
DIET_WORDS = ("gluten free", "nut free", "dairy free", "vegan", "vegetarian", "halal")
DIET_LABELS = {
    "gluten_free": ("Gluten free", "diet_gluten_free"),
    "vegan": ("Vegan", "diet_vegan"),
    "vegetarian": ("Vegetarian", "diet_vegetarian"),
    "halal": ("Halal", "diet_halal"),
}
RECORDED = {True: "yes", False: "no", None: "not recorded"}
COULD_NOT_CONFIRM = "We could not confirm this route — please plan it again."


def place_phrase(services, loc: dict) -> str:
    """Where one placement is, naming floor, aisle, rack and shelf where they exist (FR-10)."""
    node = services.store.nodes[loc["node_id"]]
    kind = loc["location_type"]
    if kind in ("HOME", "CHILLER") or (kind == "SEASONAL" and node.node_type == "rack"):
        return f"floor {node.level}, aisle {node.aisle}, rack {node.rack}, shelf {loc['shelf_no']}"
    if kind == "PROMO_ENDCAP":
        return f"floor {node.level}, aisle {node.aisle}, end of the aisle"
    if kind == "COUNTER":
        return f"floor {node.level}, {node.zone} — ask a colleague"
    if kind == "ASSISTED":
        return f"floor {node.level}, locked {node.zone} cabinet — ask a colleague"
    return f"floor {node.level}, {node.zone} bin"


def locations_for(services, sku: str) -> list[dict]:
    """Placements a shopper should be told about. An empty seasonal bay is not offered (EC-24)."""
    in_stock = services.stock.availability(sku) is Availability.IN_STOCK
    return [
        {"node_id": p.node_id, "location_type": p.location_type, "shelf_no": p.shelf_no}
        for p in services.planogram.for_sku(sku)
        if in_stock or not p.seasonal
    ]


def product_label(services, sku: str) -> str:
    p = services.catalogue.by_sku(sku)
    return f"{p.name} {p.size}" if p else sku


def dietary_status(services, sku: str, wanted) -> str:
    """The recorded status of each property the shopper asked about — never inferred (NFR-03)."""
    p = services.catalogue.by_sku(sku)
    parts = []
    for want in wanted:
        if want in DIET_LABELS:
            label, field = DIET_LABELS[want]
            parts.append(f" {label}: {RECORDED[getattr(p, field)]}.")
    return "".join(parts)


def statement(services, sku: str, substitutes: list[str] | None, wanted=()) -> str:
    availability = services.stock.availability(sku)
    head = f"{product_label(services, sku)} — {AVAILABILITY_TEXT[availability]}."
    where = "; ".join(place_phrase(services, loc) for loc in locations_for(services, sku))
    if availability is Availability.IN_STOCK:
        body = f" {where[0].upper()}{where[1:]}." if where else " Location not recorded."
    elif availability is Availability.NOT_RANGED or not where:
        body = ""
    else:
        body = f" It is usually at {where}."  # EC-13
    if availability is not Availability.IN_STOCK and substitutes is not None:
        if substitutes:
            alts = ", ".join(product_label(services, s) for s in substitutes)
            body += f" In stock instead: {alts}."
        else:
            body += " No in-stock alternative matches its recorded dietary needs."
    return head + body + dietary_status(services, sku, wanted)


def compose_results(services, s: dict, subjects: list[str]) -> list[str]:
    lines = []
    statuses = s.get("term_status") or []
    for i, status in enumerate(statuses):
        text = s["terms"][i]["text"]
        if status == "category":
            names = ", ".join(product_label(services, k) for k in s["candidates"][i][:3])
            lines.append(f"“{text}” is a whole category, {s['category'][i]} — for example {names}.")
        elif status == "not_catalogued":  # EC-50 — said plainly, never a nearest product
            lines.append(
                f"Barcode {text} is not in this store's catalogue — it may be another shop's "
                "product, or not a grocery product."
            )
        elif status == "unresolved":
            near = s["suggestions"][i]
            lines.append(
                f"We don't recognise “{text}”."
                + (f" Did you mean: {', '.join(near)}?" if near else "")
            )
    substitutes = s.get("substitutes") or {}
    wanted = (s.get("parsed") or {}).get("dietary_required") or ()
    lines += [statement(services, sku, substitutes.get(sku), wanted) for sku in subjects]
    lines += list(s.get("notes") or [])
    if s.get("message"):
        lines.append(s["message"])
    return lines


def _node_phrase(services, node_id: str) -> str:
    node = services.store.nodes[node_id]
    if node.node_type == "entrance":
        return "the entrance"
    if node.node_type == "rack":
        return f"floor {node.level}, aisle {node.aisle}, rack {node.rack}"
    if node.node_type == "aisle_end":
        end = "north" if node_id.endswith("-N") else "south"
        return f"floor {node.level}, the {end} end of aisle {node.aisle}"
    return f"floor {node.level}, {node.zone}"


def directions(services, route: dict | None) -> list[str]:
    """One line per fact: start, every floor change, every stop, the till, the total."""
    if not route:
        return []
    if route["kind"] == "none":
        return [route["message"]]
    engine, nodes = services.engine, route["nodes"]
    stop_at = dict(zip(route["stop_at"], route["stops"], strict=True))
    if len(nodes) == 1:  # EC-25 — already there
        stop = route["stops"][0]
        return [f"You are already there — {_stop_line(services, stop)}."]
    lines = [f"Start at {_node_phrase(services, nodes[0])}."]
    for i in range(1, len(nodes)):
        edge = engine.graph.edge(nodes[i - 1], nodes[i], route["step_free"])
        if edge.kind in VERTICAL:
            level = services.store.nodes[nodes[i]].level
            way = "up" if level > services.store.nodes[nodes[i - 1]].level else "down"
            lines.append(f"Take the {edge.kind} {way} to floor {level}.")
        if i in stop_at:
            lines.append(f"{_capital(_stop_line(services, stop_at[i]))}.")
    if route.get("till"):
        lines.append(f"Finish at checkout {int(route['till'].rsplit('-', 1)[1])}.")
    lines.append(f"Total walk about {round(route['distance_m'])} m.")
    return lines


def _stop_line(services, stop: dict) -> str:
    placement = next(
        p for p in services.planogram.for_sku(stop["sku"]) if p.node_id == stop["node_id"]
    )
    loc = {"node_id": placement.node_id, "location_type": placement.location_type,
           "shelf_no": placement.shelf_no}  # fmt: skip
    return f"{place_phrase(services, loc)}: pick up {product_label(services, stop['sku'])}"


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


NUMBER = re.compile(r"\d+(?:\.\d+)?")


LOCATION_WORDS = ("floor", "aisle", "rack", "shelf")


def claims(line: str) -> tuple[list[str], set[str], list[str], list[str]]:
    """The checkable content of a line: its numbers, the connectors it names, every dietary
    word (AC-25), and the words floor, aisle, rack and shelf — so the reworded directions still
    name each, read as plain text (AC-27)."""
    low = line.lower()
    words = re.findall(r"[a-z]+", low)
    diet = sorted(w for w in DIET_WORDS for _ in re.finditer(rf"\b{w}\b", low))
    places = sorted(w for w in words if w in LOCATION_WORDS)
    return sorted(NUMBER.findall(line)), {v for v in VERTICAL if v in words}, diet, places
