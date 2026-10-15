"""What the page shows, as plain data — so it is tested without a browser (P7-R02), and sent to
the Next.js page as JSON (C-03, hld.md §4). No framework here: the API is the only module that
knows it is a web service."""

from dataclasses import asdict, dataclass

from graph.templates import product_label
from present.floorplate import floor_plates


def start_options(services) -> dict[int, list[tuple[str, str]]]:
    """Per floor, the places a shopper can say they are: the entrance, then every aisle (FR-15).
    Built from the map, so a different store offers its own aisles with no code change."""
    graph, nodes = services.engine.graph, services.store.nodes
    options: dict[int, list[tuple[str, str]]] = {}
    for level in sorted({n.level for n in graph.nodes.values()}):
        here = []
        if nodes[graph.entrance].level == level:
            here.append(("Entrance", graph.entrance))
        ends: dict[int, str] = {}
        for node_id in sorted(graph.nodes):
            n = nodes[node_id]
            if n.level == level and n.node_type == "aisle_end":
                ends[n.aisle] = node_id  # the last end in ID order: the front of the aisle
        here += [(f"Aisle {a}", ends[a]) for a in sorted(ends)]
        options[level] = here
    return options


def suggestions(services) -> list[dict]:
    """FR-28 — what the search box can suggest: every product this store carries, by the label
    that searches straight to it, with the words it answers to and whether it is on the shelf.
    Sent once with the store; the phone matches it as the shopper types, so no keystroke reaches
    the server. A product not carried here is never suggested (EC-04 stays a search answer)."""
    out = []
    for sku, p in services.store.products.items():
        pos = services.stock.positions([sku])[sku]
        if not pos.ranged:
            continue
        out.append({
            "sku": sku,
            "label": product_label(services, sku),
            "terms": [p.name, p.brand, *p.synonyms],
            "in_stock": pos.shelf_qty > 0,
            "popularity": p.popularity,
        })  # fmt: skip
    return sorted(out, key=lambda r: (-r["popularity"], r["label"]))


def floor_names(services) -> dict[int, str]:
    return {n.level: n.floor_name or f"Floor {n.level}" for n in services.store.nodes.values()}


@dataclass(frozen=True)
class Row:
    sku: str
    label: str
    statement: str
    availability: str
    price: str = ""  # FR-29 — from the catalogue
    tags: tuple[str, ...] = ()  # FR-29 — only properties the record says are true (NFR-03)
    qty: int = 1  # FR-30 — "2 x milk"


DIET_TAGS = (  # attribute, words shown — passed through from the record, never inferred
    ("diet_vegan", "Vegan"),
    ("diet_vegetarian", "Vegetarian"),
    ("diet_gluten_free", "Gluten free"),
    ("diet_halal", "Halal"),
)


def recorded_tags(product) -> tuple[str, ...]:
    """FR-29 — the dietary properties this product's record says it has. A property recorded as
    false or not recorded at all is simply not shown: nothing here says a product lacks one
    (NFR-03). Vegan implies vegetarian, so the second is left out beside the first."""
    tags = tuple(words for attr, words in DIET_TAGS if getattr(product, attr) is True)
    return tuple(t for t in tags if not (t == "Vegetarian" and "Vegan" in tags))


@dataclass(frozen=True)
class Groups:
    available: list[Row]
    unavailable: list[Row]
    notes: list[str]


def group_results(services, s: dict) -> Groups:
    """FR-21 — available first. Statements are the verified ones, matched to their product."""
    resolved = s.get("resolved") or {}
    skus = list(dict.fromkeys(resolved[k] for k in sorted(resolved, key=int)))
    if s.get("action") == "plan":
        skus = list(dict.fromkeys(b["sku"] for b in s.get("basket") or []))
    terms, qty = s.get("terms") or [], {}
    for k, sku in resolved.items():
        if int(k) < len(terms):
            qty[sku] = qty.get(sku, 0) + int(terms[int(k)].get("qty") or 1)
    lines, used, rows = list(s.get("results") or []), set(), []
    for sku in skus:
        label = product_label(services, sku)
        line = next((ln for ln in lines if ln.startswith(f"{label} — ")), label)
        used.add(line)
        p = services.catalogue.by_sku(sku)
        rows.append(Row(sku, label, line, (s.get("availability") or {}).get(sku, "unknown"),
                        price=f"£{p.price_gbp:.2f}" if p and p.price_gbp is not None else "",
                        tags=recorded_tags(p) if p else (), qty=qty.get(sku, 1)))  # fmt: skip
    return Groups(
        available=[r for r in rows if r.availability == "in_stock"],
        unavailable=[r for r in rows if r.availability != "in_stock"],
        notes=[ln for ln in lines if ln not in used],
    )


def addable(groups: Groups) -> list[str]:
    """FR-22 — the one action moves only the available items."""
    return [r.sku for r in groups.available]


# ── one response for the page — hld.md §4 ───────────────────────────────────────────────────

WHY_THIS_ORDER = (
    "Why this order: the highest floor first, one pass per floor, ending at the checkouts."
)


def degraded_notice(state: dict) -> str | None:
    used = state.get("degraded") or []
    if not used:
        return None
    names = ", ".join(n.replace("_", " ") for n in used)
    return (
        f"Plain wording: the language model wasn't used for {names}. Every fact above comes "
        "from the store data either way."
    )


def route_view(services, state: dict) -> dict | None:
    """FR-20 — the route twice: the directions (the accessible route, NFR-10) and the plates."""
    r = state.get("route")
    if not r:
        return None
    if r["kind"] == "none":
        return {"kind": "none", "message": r["message"], "directions": [], "excluded": [],
                "why": None, "plates": []}  # fmt: skip
    return {
        "kind": r["kind"],
        "message": None,
        "directions": list(state.get("directions") or []),
        "excluded": [item["message"] for item in r.get("excluded") or []],
        "why": WHY_THIS_ORDER if r["kind"] == "multi" else None,
        # SVG drawn by our code from validated map data, with no free text in it (AC-13)
        "plates": [
            {
                "level": p.level,
                "name": p.floor_name,
                "svg": p.svg,
                "picks": [
                    {"n": n, "node": node, "label": label, "where": where}
                    for n, node, label, where in p.picks
                ],
            }  # fmt: skip
            for p in floor_plates(services, r)
        ],  # fmt: skip
    }


def page_view(services, state: dict, pending: dict | None = None) -> dict:
    """Everything the page draws after one request, already verified."""
    if pending:
        return {"pending": pending, "notice": None, "available": [], "unavailable": [],
                "notes": [], "addable": [], "offer_add": False, "route": None,
                "degraded": None, "split": state.get("split") or []}  # fmt: skip
    if not state.get("results") and state.get("message"):
        return {
            "pending": None,
            "notice": state["message"],
            "available": [],
            "unavailable": [],
            "notes": [],
            "addable": [],
            "offer_add": False,
            "route": None,
            "degraded": None,
            "split": [],
        }  # fmt: skip — a run that made no claim says why (EC-01, EC-10)
    groups = group_results(services, state)
    many = len(groups.available) + len(groups.unavailable) > 1
    return {
        "pending": None,
        "notice": None,
        "available": [asdict(r) for r in groups.available],
        "unavailable": [asdict(r) for r in groups.unavailable],
        "notes": groups.notes,
        "addable": addable(groups),
        "offer_add": state.get("action") != "plan" and (many or state.get("shape") != "term"),
        "route": route_view(services, state),
        "degraded": degraded_notice(state),
        "split": state.get("split") or [],  # shown, with a way to search it as one (FR-02)
    }
