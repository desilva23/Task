"""What the page shows, as plain data — so it is tested without a browser (P7-R02)."""

import hashlib
from dataclasses import dataclass

from graph.templates import product_label


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


def floor_names(services) -> dict[int, str]:
    return {n.level: n.floor_name or f"Floor {n.level}" for n in services.store.nodes.values()}


@dataclass(frozen=True)
class Row:
    sku: str
    label: str
    statement: str
    availability: str


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
    lines, used, rows = list(s.get("results") or []), set(), []
    for sku in skus:
        label = product_label(services, sku)
        line = next((ln for ln in lines if ln.startswith(f"{label} — ")), label)
        used.add(line)
        rows.append(Row(sku, label, line, (s.get("availability") or {}).get(sku, "unknown")))
    return Groups(
        available=[r for r in rows if r.availability == "in_stock"],
        unavailable=[r for r in rows if r.availability != "in_stock"],
        notes=[ln for ln in lines if ln not in used],
    )


def addable(groups: Groups) -> list[str]:
    """FR-22 — the one action moves only the available items."""
    return [r.sku for r in groups.available]


# ── the barcode scan — hld.md §3.5 ─────────────────────────────────────────────────────────

NO_BARCODE = (
    "No barcode found in that photo. Hold the barcode flat and close enough to fill the frame, "
    "in good light — or type the numbers under it."
)
SEVERAL = "There's more than one barcode in that photo — scan one product at a time."


class PhotoLatch:
    """The camera widget hands back the same photo on every page run; look each one up once
    (EC-54). Kept in session state, so it holds a digest, never the photo."""

    def __init__(self):
        self._seen: str | None = None

    def new(self, photo: bytes | None) -> bool:
        if photo is None:
            return False
        digest = hashlib.sha256(photo).hexdigest()
        fresh, self._seen = digest != self._seen, digest
        return fresh


def scan_choice(codes: list[str]) -> tuple[str | None, str | None]:
    """The code to look up, or why there is none. Two codes are never chosen between (EC-53)."""
    if len(codes) == 1:
        return codes[0], None
    return None, NO_BARCODE if not codes else SEVERAL
