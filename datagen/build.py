"""Assemble the demo store from the curated catalogue and the map, then write six CSVs.

The seed draws only the details — SKUs, barcodes, prices, popularity, stock, shelf positions,
facing counts and most promotional end caps. Anchors in catalogue.py override it.
"""

import csv
import io
import random
from pathlib import Path

from datagen.catalogue import AISLES, DIET, DUMP_BINS, PROMO_ENDCAPS, SPOTS, parse_items
from datagen.layout import RACKS_PER_AISLE, aisle_id, build_map, rack_id

DEFAULT_SEED = 20261013
STORE_ID = "SBY-DEMO-001"

STORE = {
    "store_id": STORE_ID,
    "store_name": "Sainsbury's Demo Superstore",
    "data_provenance": "synthetic",
    "planogram_version": "2026-10-01",
    "stock_as_of": "2026-10-09T08:40:00Z",
}

COLUMNS = {
    "store.csv": ["key", "value"],
    "products.csv": [
        "sku", "name", "brand", "size", "barcode", "department", "aisle_category", "synonyms",
        "diet_gluten_free", "diet_vegan", "diet_vegetarian", "diet_halal", "allergens_contains",
        "age_restricted", "price_gbp", "own_brand", "popularity",
    ],
    "stock.csv": ["sku", "ranged", "shelf_qty"],
    "planogram.csv": [
        "sku", "node_id", "location_type", "shelf_no", "facing_from", "facing_count", "seasonal",
    ],
    "map_nodes.csv": [
        "node_id", "node_type", "level", "floor_name", "aisle", "rack", "shelf_count", "zone",
        "x_m", "y_m", "is_open",
    ],
    "map_edges.csv": [
        "edge_id", "from_node", "to_node", "kind", "weight_m", "penalty_m", "bidirectional",
        "step_free", "trolley", "is_open",
    ],
}  # fmt: skip
FILES = tuple(COLUMNS)

TOKEN = {"t": "true", "f": "false", "": ""}


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _ean13(rng: random.Random, taken: set[str]) -> str:
    """A synthetic EAN-13 in the restricted in-store range (prefix 20), valid check digit."""
    while True:
        body = "20" + "".join(str(rng.randrange(10)) for _ in range(10))
        odd, even = sum(map(int, body[0::2])), sum(map(int, body[1::2]))
        code = body + str((10 - (odd + 3 * even) % 10) % 10)
        if code not in taken:
            taken.add(code)
            return code


def _product(item, department, category, diet, price, age, rng, skus, barcodes, counter):
    o = item["overrides"]
    gf, vegan, veg, halal, allergens = DIET[diet]
    sku = o.get("sku") or next(skus)
    return {
        "sku": sku,
        "name": item["name"],
        "brand": item["brand"],
        "size": item["size"],
        "barcode": "" if counter else _ean13(rng, barcodes),
        "department": department,
        "aisle_category": category,
        "synonyms": item["synonyms"],
        "diet_gluten_free": TOKEN[o["gf"]] if "gf" in o else gf,
        "diet_vegan": TOKEN[o["vegan"]] if "vegan" in o else vegan,
        "diet_vegetarian": TOKEN[o["veg"]] if "veg" in o else veg,
        "diet_halal": TOKEN[o["halal"]] if "halal" in o else halal,
        "allergens_contains": o.get("allergens", allergens),
        "age_restricted": _bool(o["age"] == "t") if "age" in o else _bool(age),
        "price_gbp": o.get("price") or f"{rng.uniform(*price):.2f}",
        "own_brand": _bool(item["brand"] == "Own Brand"),
        "popularity": o.get("pop") or f"{rng.uniform(0.05, 0.95):.2f}",
    }


def _sku_source(rng: random.Random):
    reserved = {"7123456"}  # the Coca-Cola anchor
    for n in rng.sample(range(1_000_000, 10_000_000), 400):
        if str(n) not in reserved:
            yield str(n)


def build_rows(seed: int) -> dict[str, list[dict[str, str]]]:
    rng = random.Random(seed)
    skus, barcodes = _sku_source(rng), set()
    products, stock, placements = [], [], []

    def stock_row(product, o):
        ranged = o.get("ranged") != "f"
        qty = int(o["stock"]) if "stock" in o else (rng.randint(3, 48) if ranged else 0)
        stock.append({"sku": product["sku"], "ranged": _bool(ranged), "shelf_qty": str(qty)})
        return qty

    def place(sku, node, kind, shelf=None, from_=None, count=None, seasonal=False):
        placements.append({
            "sku": sku, "node_id": node, "location_type": kind,
            "shelf_no": "" if shelf is None else str(shelf),
            "facing_from": "" if from_ is None else str(from_),
            "facing_count": "" if count is None else str(count),
            "seasonal": _bool(seasonal),
        })  # fmt: skip

    endcap_pool = []  # (sku, level, aisle) eligible for a seeded promotional end cap
    by_name = {}
    for a in AISLES:
        racked = []
        for item in parse_items(a.items):
            o = item["overrides"]
            p = _product(item, a.department, a.category, a.diet, a.price, a.age_restricted,
                         rng, skus, barcodes, counter=False)  # fmt: skip
            products.append(p)
            by_name[(p["name"], p["size"])] = p["sku"]
            qty = stock_row(p, o)
            if o.get("ranged") == "f" or "unplaced" in o:
                continue
            racked.append((p, o, qty))

        free = list(range(1, RACKS_PER_AISLE + 1))
        fixed = {int(o["rack"]): (p, o) for p, o, _ in racked if "rack" in o}
        for r in fixed:
            free.remove(r)
        order = [(r, p, o) for r, (p, o) in fixed.items()]
        order += [(free.pop(0), p, o) for p, o, _ in racked if "rack" not in o]
        # spare racks hold a second facing of the aisle's in-stock best sellers; a product
        # pinned to a rack keeps exactly the placements its anchor declares
        sellers = sorted(
            (x for x in racked if x[2] > 0 and "rack" not in x[1]),
            key=lambda x: -float(x[0]["popularity"]),
        )
        order += [(r, sellers[i % len(sellers)][0], {}) for i, r in enumerate(free)]

        seasonal = a.placement == "SEASONAL"
        for r, p, o in sorted(order, key=lambda x: x[0]):
            shelf = int(o["shelf"]) if "shelf" in o else rng.randint(1, a.shelf_count)
            count = int(o["facings"]) if "facings" in o else rng.randint(1, 4)
            place(p["sku"], rack_id(a.level, a.number, r), a.placement, shelf, 1, count, seasonal)
            if "endcap" in o:
                place(p["sku"], aisle_id(a.level, a.number, o["endcap"]), "PROMO_ENDCAP")
        endcap_pool += [
            (p["sku"], a.level, a.number)
            for p, o, qty in racked
            if qty > 0 and "endcap" not in o and not seasonal
        ]

    for s in SPOTS:
        for item in parse_items(s.items):
            p = _product(item, s.department, s.category, s.diet, s.price, s.age_restricted,
                         rng, skus, barcodes, counter=s.location_type == "COUNTER")  # fmt: skip
            products.append(p)
            stock_row(p, item["overrides"])
            place(p["sku"], s.node_id, s.location_type)

    for name, size, node in DUMP_BINS:
        place(by_name[(name, size)], node, "DUMP_BIN")
    for sku, level, aisle in rng.sample(endcap_pool, PROMO_ENDCAPS - 1):
        place(sku, aisle_id(level, aisle, rng.choice("NS")), "PROMO_ENDCAP")

    shelf_counts = {(a.level, a.number): a.shelf_count for a in AISLES}
    zones = {(a.level, a.number): a.category for a in AISLES}
    nodes, edges = build_map(shelf_counts, zones)

    def num(v):
        return "" if v is None else str(v)

    node_rows = [{
        "node_id": n.node_id, "node_type": n.node_type, "level": str(n.level),
        "floor_name": n.floor_name, "aisle": num(n.aisle), "rack": num(n.rack),
        "shelf_count": num(n.shelf_count), "zone": n.zone,
        "x_m": f"{n.x_m:.1f}", "y_m": f"{n.y_m:.1f}", "is_open": "true",
    } for n in nodes]  # fmt: skip
    edge_rows = [{
        "edge_id": f"E{i:04}", "from_node": e.from_node, "to_node": e.to_node, "kind": e.kind,
        "weight_m": f"{e.weight_m:.1f}", "penalty_m": f"{e.penalty_m:.1f}",
        "bidirectional": "true", "step_free": _bool(e.step_free), "trolley": _bool(e.trolley),
        "is_open": "true",
    } for i, e in enumerate(edges, start=1)]  # fmt: skip

    def pk(row):
        return (row["sku"], row["node_id"], row["shelf_no"], row["facing_from"])

    return {
        "store.csv": [{"key": k, "value": v} for k, v in STORE.items()],
        "products.csv": sorted(products, key=lambda r: r["sku"]),
        "stock.csv": sorted(stock, key=lambda r: r["sku"]),
        "planogram.csv": sorted(placements, key=pk),
        "map_nodes.csv": sorted(node_rows, key=lambda r: r["node_id"]),
        "map_edges.csv": edge_rows,
    }


def to_csv(name: str, rows: list[dict[str, str]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS[name], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def build_store(seed: int = DEFAULT_SEED) -> dict[str, str]:
    """The six files as text, keyed by file name."""
    return {name: to_csv(name, rows) for name, rows in build_rows(seed).items()}


def write_store(folder: Path, seed: int = DEFAULT_SEED) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in build_store(seed).items():
        (folder / name).write_bytes(text.encode("utf-8"))
