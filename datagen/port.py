"""SBY-PORT-002 — the portability store (AC-09, schema.md §8).

Same catalogue and stock as the demo store — the generator's own demo rows, unchanged — on a
differently shaped map: two floors, 15 aisles (8 + 7) of five racks, several categories sharing
an aisle so a rack holds several products on different shelves, four tills, and both locked
cabinets on floor 1. Only the map and the planogram move.
"""

from datagen.catalogue import AISLES, SPOTS, parse_items
from datagen.layout import Floor, aisle_id, build_map, rack_id

STORE_ID = "SBY-PORT-002"
STORE_NAME = "Sainsbury's Portability Test Store"
RACKS = 5
SHELVES = 5
FLOORS = (Floor(0, "Ground Floor", 8), Floor(1, "First Floor", 7))
REAR_CORE_X = 54.0
# catalogue aisles, in catalogue order, packed into the physical aisles in this order
PACKING = {
    0: [3, 3, 2, 2, 2, 2, 2, 2],  # 18 catalogue aisles on the ground floor
    1: [3, 3, 2, 2, 3, 2, 3],  # 18 on the first
}
EXTRAS = (
    ("F0-ENTRANCE", "entrance", 6.0, 36.0, "Entrance", "F0-A01-S"),
    *(
        (f"F0-TILL-{i:02}", "till", 6.0 * (i + 2), 34.0, "Checkouts", f"F0-A{i + 2:02}-S")
        for i in range(1, 5)
    ),
    ("F0-CTR-01", "counter", 12.0, 2.0, "Deli Counter", "F0-A02-N"),
    ("F0-CTR-02", "counter", 24.0, 2.0, "Fish Counter", "F0-A04-N"),
    ("F0-CTR-03", "counter", 36.0, 2.0, "Bakery Counter", "F0-A06-N"),
    ("F1-CAB-01", "cabinet", 30.0, 2.0, "Spirits", "F1-A05-N"),
    ("F1-CAB-02", "cabinet", 42.0, 2.0, "Baby", "F1-A07-N"),
    ("F0-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F0-A02-S"),
    ("F1-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F1-A02-S"),
)
SPOT_NODES = {"F2-CAB-01": "F1-CAB-02"}  # the demo's second-floor cabinet moves down


def _physical() -> dict[tuple[int, int], tuple[int, int]]:
    """Catalogue aisle (level, number) → physical aisle (level, number) here."""
    order = [(a.level, a.number) for a in AISLES]
    out, i = {}, 0
    for level, counts in PACKING.items():
        for number, count in enumerate(counts, start=1):
            for _ in range(count):
                out[order[i]] = (level, number)
                i += 1
    assert i == len(order), "PACKING must place every catalogue aisle"
    return out


def build_port_rows(demo: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    where = _physical()
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
            rack, shelf = i % RACKS + 1, i // RACKS + 1
            place(sku, rack_id(level, number, rack), kind, shelf, 2, kind == "SEASONAL")

    for p in demo["planogram.csv"]:
        kind, node = p["location_type"], p["node_id"]
        if kind == "PROMO_ENDCAP":
            level, number = catalogue_aisle[p["sku"]]
            place(p["sku"], aisle_id(level, number, node[-1]), kind)
        elif kind in ("COUNTER", "ASSISTED", "DUMP_BIN"):
            place(p["sku"], SPOT_NODES.get(node, node), kind)
    assert {s.node_id for s in SPOTS} - set(SPOT_NODES) <= {e[0] for e in EXTRAS}

    shelf_counts = {(f.level, a): SHELVES for f in FLOORS for a in range(1, f.aisles + 1)}
    zone_names = {k: " · ".join(v) for k, v in zones.items()}
    nodes, edges = build_map(shelf_counts, zone_names, FLOORS, EXTRAS, RACKS, REAR_CORE_X)

    def pk(row):
        return (row["sku"], row["node_id"], row["shelf_no"], row["facing_from"])

    store = [
        {**r, "value": STORE_ID} if r["key"] == "store_id"
        else {**r, "value": STORE_NAME} if r["key"] == "store_name"
        else r
        for r in demo["store.csv"]
    ]  # fmt: skip
    from datagen.build import edge_rows, node_rows  # shared row formatting

    assert set(stocked) == set(sku_of.values())
    return {
        "store.csv": store,
        "products.csv": demo["products.csv"],
        "stock.csv": demo["stock.csv"],
        "planogram.csv": sorted(placements, key=pk),
        "map_nodes.csv": sorted(node_rows(nodes), key=lambda r: r["node_id"]),
        "map_edges.csv": edge_rows(edges),
    }
