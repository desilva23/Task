"""Another building for the same catalogue (FR-25, AC-09, schema.md §8).

The demo store's products and stock rows, unchanged, on a differently shaped map: its own floors
and aisles, catalogue aisles packed into physical ones, counters and cabinets where that store
keeps them, and its own planogram. Only the map and the planogram move — and, for a store that
asks for it, the shelf quantities. The portability store (two floors) and the city flagship
(five) are two specs of this one builder; no code knows which store it is drawing.
"""

import random
from dataclasses import dataclass, field

from datagen.catalogue import AISLES, SPOTS, parse_items
from datagen.layout import Floor, aisle_id, build_map, rack_id


@dataclass(frozen=True)
class Variant:
    store_id: str
    name: str
    floors: tuple[Floor, ...]
    packing: dict[int, list[int]]  # per floor: how many catalogue aisles share each aisle
    extras: tuple  # entrance, tills, counters, cabinets, bins — as layout.EXTRAS
    rear_core_x: float  # beyond the widest floor's last aisle
    racks: int = 5
    shelves: int = 5
    spot_nodes: dict[str, str] = field(default_factory=dict)  # a demo spot that moves
    restock_seed: int | None = None


def _physical(v: "Variant") -> dict[tuple[int, int], tuple[int, int]]:
    """Catalogue aisle (level, number) → physical aisle (level, number) here."""
    order = [(a.level, a.number) for a in AISLES]
    out, i = {}, 0
    for level, counts in v.packing.items():
        for number, count in enumerate(counts, start=1):
            for _ in range(count):
                out[order[i]] = (level, number)
                i += 1
    assert i == len(order), "the packing must place every catalogue aisle"
    return out


def build_variant_rows(
    demo: dict[str, list[dict[str, str]]], v: "Variant"
) -> dict[str, list[dict[str, str]]]:
    """The demo store's catalogue in another building: ``v``'s floors, aisles and spots, its
    own planogram, and — when ``v.restock_seed`` is set — its own shelf quantities."""
    where = _physical(v)
    sku_of = {(p["name"], p["size"]): p["sku"] for p in demo["products.csv"]}
    stocked = {s["sku"]: s for s in demo["stock.csv"]}
    by_physical: dict[tuple[int, int], list] = {}
    catalogue_aisle = {}
    zones: dict[tuple[int, int], list[str]] = {}
    for a in AISLES:
        phys = where[(a.level, a.number)]
        zones.setdefault(phys, []).append(a.category)
        for item in parse_items(a.items):
            o = item["overrides"]
            sku = sku_of[(item["name"], item["size"])]
            catalogue_aisle[sku] = phys
            if o.get("ranged") == "f" or "unplaced" in o:
                continue
            by_physical.setdefault(phys, []).append((sku, a.placement))

    placements = []

    def place(sku, node, kind, shelf=None, count=None, seasonal=False):
        placements.append({
            "sku": sku, "node_id": node, "location_type": kind,
            "shelf_no": "" if shelf is None else str(shelf),
            "facing_from": "" if shelf is None else "1",
            "facing_count": "" if count is None else str(count),
            "seasonal": "true" if seasonal else "false",
        })  # fmt: skip

    for (level, number), items in sorted(by_physical.items()):
        for i, (sku, kind) in enumerate(items):  # round the racks, then up a shelf
            rack, shelf = i % v.racks + 1, i // v.racks + 1
            place(sku, rack_id(level, number, rack), kind, shelf, 2, kind == "SEASONAL")

    for p in demo["planogram.csv"]:
        kind, node = p["location_type"], p["node_id"]
        if kind == "PROMO_ENDCAP":
            level, number = catalogue_aisle[p["sku"]]
            place(p["sku"], aisle_id(level, number, node[-1]), kind)
        elif kind in ("COUNTER", "ASSISTED", "DUMP_BIN"):
            place(p["sku"], v.spot_nodes.get(node, node), kind)
    assert {s.node_id for s in SPOTS} - set(v.spot_nodes) <= {e[0] for e in v.extras}

    shelf_counts = {(f.level, a): v.shelves for f in v.floors for a in range(1, f.aisles + 1)}
    zone_names = {k: " · ".join(z) for k, z in zones.items()}
    nodes, edges = build_map(shelf_counts, zone_names, v.floors, v.extras, v.racks, v.rear_core_x)

    def pk(row):
        return (row["sku"], row["node_id"], row["shelf_no"], row["facing_from"])

    store = [
        {**r, "value": v.store_id} if r["key"] == "store_id"
        else {**r, "value": v.name} if r["key"] == "store_name"
        else r
        for r in demo["store.csv"]
    ]  # fmt: skip
    stock = demo["stock.csv"]
    if v.restock_seed is not None:  # another branch, another morning: its own quantities
        rng = random.Random(v.restock_seed)
        stock = [
            {**s, "shelf_qty": str(rng.randint(1, 48))}
            if s["ranged"] == "true" and s["shelf_qty"] not in ("", "0")
            else s
            for s in stock
        ]  # fmt: skip — what is sold out or not carried stays so, as the demo's anchors expect
    from datagen.build import edge_rows, node_rows  # shared row formatting

    assert set(stocked) == set(sku_of.values())
    return {
        "store.csv": store,
        "products.csv": demo["products.csv"],
        "stock.csv": stock,
        "planogram.csv": sorted(placements, key=pk),
        "map_nodes.csv": sorted(node_rows(nodes), key=lambda r: r["node_id"]),
        "map_edges.csv": edge_rows(edges),
    }
