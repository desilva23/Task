"""Stock alerts for the store manager (FR-26, hld.md §3.6). Pure: two stock versions in, the
alerts and their emails out. Sending is somebody else's job (``notify``).

An alert is a change, not a state: a product is reported when it gets worse — fine to low, fine
to out, low to out — so a product that stays low is never reported twice, and no record of
past alerts is kept. A product not stocked at this branch is never reported (EC-57).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from html import escape

from config import LOW_STOCK_UNITS
from models.domain import StockPosition, Store

LOW, OUT = "low", "out"
_LEVEL = {None: 0, LOW: 1, OUT: 2}


@dataclass(frozen=True)
class Alert:
    kind: str  # low · out
    sku: str
    name: str
    units: int
    where: str


@dataclass(frozen=True)
class Email:
    kind: str
    subject: str
    text: str
    html: str


def state(pos: StockPosition | None, low: int = LOW_STOCK_UNITS) -> str | None:
    if pos is None or not pos.ranged:
        return None
    if pos.shelf_qty == 0:
        return OUT
    return LOW if pos.shelf_qty <= low else None


def where(store: Store, sku: str) -> str:
    """Every place the product is kept, in the words the shopper page uses."""
    places = []
    for p in sorted((p for p in store.placements if p.sku == sku), key=lambda p: p.node_id):
        n = store.nodes[p.node_id]
        if n.node_type in ("counter", "cabinet"):
            places.append(f"Floor {n.level}, {n.zone}")
        else:
            places.append(f"Floor {n.level}, aisle {n.aisle}, rack {n.rack}, shelf {p.shelf_no}")
    return "; ".join(places) or "no shelf in the planogram"


def changes(
    before: Mapping[str, StockPosition] | None, after: Store, low: int = LOW_STOCK_UNITS
) -> list[Alert]:
    """Products that got worse between two stock versions. ``before=None`` means alerts are
    being switched on: everything already low or out is reported once."""
    found = []
    for sku in sorted(after.stock):
        now = state(after.stock[sku], low)
        was = state(before.get(sku), low) if before is not None else None
        if now and _LEVEL[now] > _LEVEL[was]:
            p = after.products[sku]
            found.append(Alert(now, sku, f"{p.name} {p.size}", after.stock[sku].shelf_qty,
                               where(after, sku)))  # fmt: skip
    return sorted(found, key=lambda a: (_LEVEL[a.kind], a.name))


def _subject(kind: str, items: list[Alert], store: str) -> str:
    head = "Low stock" if kind == LOW else "Out of stock"
    what = items[0].name if len(items) == 1 else f"{len(items)} products"
    return f"{head} at {store}: {what}"


def emails(alerts: list[Alert], store: Store) -> list[Email]:
    """One email per kind, listing every product of that kind — none at all if nothing changed
    (EC-60). Low first, then out, in the order the manager would act on them."""
    name = store.info.store_name
    out = []
    for kind in (LOW, OUT):
        items = [a for a in alerts if a.kind == kind]
        if not items:
            continue
        intro = (f"These products are down to {LOW_STOCK_UNITS} or fewer on the shelf at {name}:"
                 if kind == LOW else f"These products have run out on the shelf at {name}:")  # fmt: skip
        lines = [f"- {a.name} (SKU {a.sku}) — {a.units} left — {a.where}" for a in items]
        text = "\n".join([intro, "", *lines, "", "Sent by Find it in store."])
        rows = "".join(
            f"<tr><td>{escape(a.name)}</td><td>{escape(a.sku)}</td><td>{a.units} left</td>"
            f"<td>{escape(a.where)}</td></tr>"
            for a in items
        )
        html = (f"<p>{escape(intro)}</p><table border='1' cellpadding='6' cellspacing='0'>"
                "<tr><th>Product</th><th>SKU</th><th>On the shelf</th><th>Where</th></tr>"
                f"{rows}</table><p>Sent by Find it in store.</p>")  # fmt: skip
        out.append(Email(kind, _subject(kind, items, name), text, html))
    return out
