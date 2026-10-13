"""The demo store map (schema.md §3, §4.5, §4.6, §8).

Every aisle runs north to south: an aisle end, six racks, an aisle end. Aisles sit 6 m apart.
A front corridor joins the south ends and a rear corridor the north ends; each meets a vertical
core through a junction. Both cores carry a lift and stairs on every span. Coordinates are
shared across floors, so the cores line up, and every walking distance equals the straight-line
distance between its endpoints.
"""

import math
from dataclasses import dataclass

RACKS_PER_AISLE = 6
AISLE_SPACING_M = 6.0
NORTH_Y, FIRST_RACK_Y, RACK_STEP_M, SOUTH_Y = 6.0, 9.0, 3.2, 28.0
REAR_CORE_X = 90.0  # beyond the widest floor's last aisle, so it lines up on every floor

LIFT_WEIGHT_M, LIFT_PENALTY_M = 6.0, 25.0  # a ~30 s wait as its walking equivalent
STAIRS_WEIGHT_M = 11.0


@dataclass(frozen=True)
class Floor:
    level: int
    name: str
    aisles: int


FLOORS = (
    Floor(0, "Fresh Food", 12),
    Floor(1, "Food Cupboard & Drinks", 14),
    Floor(2, "Home, Health & Baby", 10),
)

# Off-aisle points: (node_id, node_type, x, y, zone, the aisle end it links to)
EXTRAS = (
    ("F0-ENTRANCE", "entrance", 6.0, 36.0, "Entrance", "F0-A01-S"),
    *(
        (f"F0-TILL-{i:02}", "till", 6.0 * (i + 2), 34.0, "Checkouts", f"F0-A{i + 2:02}-S")
        for i in range(1, 7)
    ),
    ("F0-CTR-01", "counter", 12.0, 2.0, "Deli Counter", "F0-A02-N"),
    ("F0-CTR-02", "counter", 24.0, 2.0, "Fish Counter", "F0-A04-N"),
    ("F0-CTR-03", "counter", 36.0, 2.0, "Bakery Counter", "F0-A06-N"),
    ("F1-CAB-01", "cabinet", 78.0, 2.0, "Spirits", "F1-A13-N"),
    ("F2-CAB-01", "cabinet", 48.0, 2.0, "Baby", "F2-A08-N"),
    ("F0-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F0-A02-S"),
    ("F1-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F1-A02-S"),
)


@dataclass(frozen=True)
class Node:
    node_id: str
    node_type: str
    level: int
    floor_name: str
    aisle: int | None
    rack: int | None
    shelf_count: int | None
    zone: str
    x_m: float
    y_m: float


@dataclass(frozen=True)
class Edge:
    from_node: str
    to_node: str
    kind: str
    weight_m: float
    penalty_m: float = 0.0
    step_free: bool = True
    trolley: bool = True


def aisle_id(level: int, aisle: int, end: str) -> str:
    return f"F{level}-A{aisle:02}-{end}"


def rack_id(level: int, aisle: int, rack: int) -> str:
    return f"F{level}-A{aisle:02}-R{rack:02}"


def build_map(shelf_counts: dict[tuple[int, int], int], zones: dict[tuple[int, int], str]):
    """Nodes and edges for FLOORS. ``shelf_counts`` and ``zones`` are keyed by (level, aisle)."""
    nodes: list[Node] = []
    floor_of = {f.level: f.name for f in FLOORS}

    def add(node_id, node_type, level, x, y, zone, aisle=None, rack=None, shelves=None):
        nodes.append(
            Node(node_id, node_type, level, floor_of[level], aisle, rack, shelves, zone, x, y)
        )

    for f in FLOORS:
        for a in range(1, f.aisles + 1):
            x, zone = AISLE_SPACING_M * a, zones[(f.level, a)]
            add(aisle_id(f.level, a, "N"), "aisle_end", f.level, x, NORTH_Y, zone, aisle=a)
            for r in range(1, RACKS_PER_AISLE + 1):
                y = round(FIRST_RACK_Y + RACK_STEP_M * (r - 1), 1)
                shelves = shelf_counts[(f.level, a)]
                add(rack_id(f.level, a, r), "rack", f.level, x, y, zone, a, r, shelves)
            add(aisle_id(f.level, a, "S"), "aisle_end", f.level, x, SOUTH_Y, zone, aisle=a)
        add(f"F{f.level}-X01", "junction", f.level, 0.0, SOUTH_Y, "Front Corridor")
        add(f"F{f.level}-X02", "junction", f.level, REAR_CORE_X, NORTH_Y, "Rear Corridor")
        add(f"F{f.level}-CORE-FRONT", "core", f.level, 0.0, 32.0, "Front Core")
        add(f"F{f.level}-CORE-REAR", "core", f.level, REAR_CORE_X, 2.0, "Rear Core")
    for node_id, node_type, x, y, zone, _ in EXTRAS:
        add(node_id, node_type, int(node_id[1]), x, y, zone)

    at = {n.node_id: n for n in nodes}

    def walk(a: str, b: str, kind: str) -> Edge:
        d = math.hypot(at[a].x_m - at[b].x_m, at[a].y_m - at[b].y_m)
        return Edge(a, b, kind, round(d, 1))

    edges: list[Edge] = []
    for f in FLOORS:
        lv, n = f.level, f.aisles
        for a in range(1, n + 1):
            chain = [aisle_id(lv, a, "N")]
            chain += [rack_id(lv, a, r) for r in range(1, RACKS_PER_AISLE + 1)]
            chain += [aisle_id(lv, a, "S")]
            edges += [walk(p, q, "aisle") for p, q in zip(chain, chain[1:], strict=False)]
        for end in ("N", "S"):
            edges += [
                walk(aisle_id(lv, a, end), aisle_id(lv, a + 1, end), "corridor")
                for a in range(1, n)
            ]
        edges += [
            walk(f"F{lv}-X01", aisle_id(lv, 1, "S"), "corridor"),
            walk(f"F{lv}-X01", f"F{lv}-CORE-FRONT", "corridor"),
            walk(f"F{lv}-X02", aisle_id(lv, n, "N"), "corridor"),
            walk(f"F{lv}-X02", f"F{lv}-CORE-REAR", "corridor"),
        ]
    for core in ("FRONT", "REAR"):
        for lower in range(len(FLOORS) - 1):
            a, b = f"F{lower}-CORE-{core}", f"F{lower + 1}-CORE-{core}"
            edges.append(Edge(a, b, "lift", LIFT_WEIGHT_M, LIFT_PENALTY_M))
            edges.append(Edge(a, b, "stairs", STAIRS_WEIGHT_M, step_free=False, trolley=False))
    for node_id, *_, link in EXTRAS:
        edges.append(walk(node_id, link, "corridor"))
    return nodes, edges
