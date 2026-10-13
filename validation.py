"""Startup validation of a store folder (lld.md §13; the rules are schema.md §7).

``load_store`` runs four stages — parse, within-file, referential, graph — and collects every
fault in a stage before stopping, so an author fixes many faults per round trip and a later
stage never reports noise caused by an earlier one. It returns a ``Store`` only when every
refusal passes (constitution Principle VI); warnings ride along on the store.

Every cell is read as text and typed by an explicit parser. Nothing is inferred, so an empty
dietary cell cannot become ``False`` and a SKU cannot lose a digit (schema.md §2.2, §2.4).
"""

import csv
import io
import math
import re
from collections import Counter, defaultdict, deque
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from errors import Fault, StoreDataError
from models.domain import (
    MapEdge,
    MapNode,
    Placement,
    Product,
    StockPosition,
    Store,
    StoreInfo,
)

# ── column specifications: (type, requirement) — Y required · N optional · 3 three-state ────
SPEC = {
    "products.csv": {
        "sku": ("text", "Y"),
        "name": ("text", "Y"),
        "brand": ("text", "Y"),
        "size": ("text", "Y"),
        "barcode": ("text", "N"),
        "department": ("text", "Y"),
        "aisle_category": ("text", "Y"),
        "synonyms": ("list", "N"),
        "diet_gluten_free": ("bool", "3"),
        "diet_vegan": ("bool", "3"),
        "diet_vegetarian": ("bool", "3"),
        "diet_halal": ("bool", "3"),
        "allergens_contains": ("allergens", "3"),
        "age_restricted": ("bool", "Y"),
        "price_gbp": ("decimal", "Y"),
        "own_brand": ("bool", "Y"),
        "popularity": ("float", "Y"),
    },
    "stock.csv": {"sku": ("text", "Y"), "ranged": ("bool", "Y"), "shelf_qty": ("int", "Y")},
    "planogram.csv": {
        "sku": ("text", "Y"),
        "node_id": ("text", "Y"),
        "location_type": ("text", "Y"),
        "shelf_no": ("int", "N"),
        "facing_from": ("int", "N"),
        "facing_count": ("int", "N"),
        "seasonal": ("bool", "Y"),
    },
    "map_nodes.csv": {
        "node_id": ("text", "Y"),
        "node_type": ("node_type", "Y"),
        "level": ("int", "Y"),
        "floor_name": ("text", "N"),
        "aisle": ("int", "N"),
        "rack": ("int", "N"),
        "shelf_count": ("int", "N"),
        "zone": ("text", "N"),
        "x_m": ("float", "Y"),
        "y_m": ("float", "Y"),
        "is_open": ("bool", "Y"),
    },
    "map_edges.csv": {
        "edge_id": ("edge_id", "Y"),
        "from_node": ("text", "Y"),
        "to_node": ("text", "Y"),
        "kind": ("kind", "Y"),
        "weight_m": ("float", "Y"),
        "penalty_m": ("float", "Y"),
        "bidirectional": ("bool", "Y"),
        "step_free": ("bool", "Y"),
        "trolley": ("bool", "Y"),
        "is_open": ("bool", "Y"),
    },
}
STORE_KEYS = ("store_id", "store_name", "data_provenance", "planogram_version", "stock_as_of")
PRIMARY_KEYS = {
    "products.csv": ("sku",),
    "stock.csv": ("sku",),
    "planogram.csv": ("sku", "node_id", "shelf_no", "facing_from"),
    "map_nodes.csv": ("node_id",),
    "map_edges.csv": ("edge_id",),
}
MAY_BE_EMPTY = {"planogram.csv"}

NODE_TYPES = {
    "rack",
    "aisle_end",
    "junction",
    "core",
    "counter",
    "cabinet",
    "bin",
    "entrance",
    "till",
}
EDGE_KINDS = {"aisle", "corridor", "lift", "escalator", "stairs"}
VERTICAL = {"lift", "escalator", "stairs"}
LOCATION_TYPES = {"HOME", "PROMO_ENDCAP", "SEASONAL", "DUMP_BIN", "CHILLER", "ASSISTED", "COUNTER"}
# location_type → {permitted node_type: shelf columns required (True) or forbidden (False)}
COMPATIBLE = {
    "HOME": {"rack": True},
    "CHILLER": {"rack": True},
    "SEASONAL": {"rack": True, "bin": False},
    "PROMO_ENDCAP": {"aisle_end": False},
    "DUMP_BIN": {"bin": False},
    "ASSISTED": {"cabinet": False},
    "COUNTER": {"counter": False},
}
SHELF_COLUMNS = ("shelf_no", "facing_from", "facing_count")
NODE_ID = {
    "rack": r"F(\d+)-A(\d{2})-R(\d{2})",
    "aisle_end": r"F(\d+)-A(\d{2})-[NS]",
    "junction": r"F(\d+)-X\d{2}",
    "core": r"F(\d+)-CORE-(?:FRONT|REAR)",
    "counter": r"F(\d+)-CTR-\d{2}",
    "cabinet": r"F(\d+)-CAB-\d{2}",
    "bin": r"F(\d+)-BIN-\d{2}",
    "entrance": r"F(0)-ENTRANCE",
    "till": r"F(0)-TILL-\d{2}",
}
AISLE_REQUIRED, AISLE_OPTIONAL = {"rack", "aisle_end"}, {"counter", "cabinet", "bin"}
DIET_COLUMNS = ("diet_gluten_free", "diet_vegan", "diet_vegetarian", "diet_halal")

INT = re.compile(r"-?\d+")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
EDGE_ID = re.compile(r"E\d{4}")
SKU = re.compile(r"[1-9]\d{6}")
BARCODE = re.compile(r"\d{13}")

Row = tuple[int, dict]  # (line number, typed cells)


class _Faults(list):
    def add(self, rule: str, file: str, row: int | None, message: str) -> None:
        self.append(Fault(rule, file, row, message))


# ── stage 1 · parse ─────────────────────────────────────────────────────────────────────────


def _read(folder: Path, name: str, faults: _Faults) -> list[tuple[int, dict[str, str]]] | None:
    """Raw rows as (line, {column: text}), or None if the file cannot be read at all."""
    path = folder / name
    if not path.is_file():
        faults.add("V-01", name, None, "file is missing")
        return None
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        faults.add(
            "V-02", name, None, "file starts with a byte-order mark — save as UTF-8 without BOM"
        )
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        faults.add("V-02", name, None, f"not valid UTF-8 at byte {exc.start}")
        return None

    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader, [])
    expected = ["key", "value"] if name == "store.csv" else list(SPEC[name])
    duplicated = sorted(c for c, n in Counter(header).items() if n > 1)
    unknown = sorted(set(header) - set(expected))
    missing = [c for c in expected if c not in header]
    if duplicated or unknown or missing:
        parts = [
            f"{label}: {', '.join(cols)}"
            for label, cols in (
                ("duplicate", duplicated),
                ("unknown", unknown),
                ("missing", missing),
            )
            if cols
        ]
        faults.add("V-01", name, 1, "header does not match the schema — " + "; ".join(parts))
        return None

    rows = []
    for cells in reader:
        if not cells:
            continue  # a trailing blank line is permitted
        if len(cells) != len(header):
            faults.add(
                "V-01",
                name,
                reader.line_num,
                f"row has {len(cells)} cells, the header has {len(header)}",
            )
            continue
        rows.append((reader.line_num, dict(zip(header, cells, strict=True))))
    if not rows and name not in MAY_BE_EMPTY:
        faults.add("V-06", name, None, "file has a header but no rows")
    return rows


def _cell(name, line, column, raw, kind, req, faults):
    """Type one cell, or record its fault and return None."""
    if kind == "bool":
        if raw in ("true", "false"):
            return raw == "true"
        if raw == "" and req == "3":
            return None  # unknown — never False (schema.md §2.2)
        allowed = "true, false or empty" if req == "3" else "true or false"
        faults.add("V-04", name, line, f"{column} is {raw!r}; it must be {allowed}")
        return None
    if kind == "allergens":
        if raw == "":
            return None  # not recorded
        items = _pipe_list(name, line, column, raw, faults)
        return () if items == ("none",) else items
    if raw.strip() == "":
        if req == "Y":
            faults.add("V-06", name, line, f"{column} is required")
        return () if kind == "list" else None
    if kind == "text":
        return raw
    if kind == "list":
        return _pipe_list(name, line, column, raw, faults)
    if kind == "int" and INT.fullmatch(raw):
        return int(raw)
    if kind == "float" and NUMBER.fullmatch(raw):
        return float(raw)
    if kind == "decimal" and NUMBER.fullmatch(raw):
        try:
            return Decimal(raw)
        except InvalidOperation:
            pass
    if kind == "node_type" and raw in NODE_TYPES:
        return raw
    if kind == "kind" and raw in EDGE_KINDS:
        return raw
    if kind == "edge_id" and EDGE_ID.fullmatch(raw):
        return raw
    faults.add("V-07", name, line, f"{column} {raw!r} is not a valid {kind.replace('_', ' ')}")
    return None


def _pipe_list(name, line, column, raw, faults):
    segments = [s.strip() for s in raw.split("|")]
    if any(s == "" for s in segments):
        faults.add("V-05", name, line, f"{column} {raw!r} has an empty segment or a stray '|'")
        return ()
    return tuple(segments)


def _parse(folder: Path, faults: _Faults) -> dict[str, list[Row]] | None:
    raw = {name: _read(folder, name, faults) for name in ("store.csv", *SPEC)}
    typed: dict[str, list[Row]] = {"store.csv": raw["store.csv"] or []}
    for name, columns in SPEC.items():
        typed[name] = [
            (line, {c: _cell(name, line, c, cells[c], *columns[c], faults) for c in columns})
            for line, cells in raw[name] or []
        ]
    return None if faults else typed


# ── stage 2 · within each file ──────────────────────────────────────────────────────────────


def _within(folder: Path, t: dict[str, list[Row]], faults: _Faults) -> None:
    for name, key in PRIMARY_KEYS.items():
        seen = {}
        for line, row in t[name]:
            k = tuple(row[c] for c in key)
            if k in seen:
                faults.add("V-03", name, line, f"duplicate key {k} — first on row {seen[k]}")
            seen.setdefault(k, line)
    _store_file(folder, t["store.csv"], faults)
    _products_file(t["products.csv"], faults)

    for line, s in t["stock.csv"]:
        if s["shelf_qty"] is not None and s["shelf_qty"] < 0:
            faults.add("V-33", "stock.csv", line, f"shelf_qty {s['shelf_qty']} is negative")
        if s["ranged"] is False and (s["shelf_qty"] or 0) > 0:
            faults.add("V-31", "stock.csv", line, "not ranged here but has stock on the shelf")

    shelves = defaultdict(list)
    for line, p in t["planogram.csv"]:
        if p["location_type"] not in LOCATION_TYPES:
            faults.add(
                "V-42",
                "planogram.csv",
                line,
                f"location_type {p['location_type']!r} is not one of {sorted(LOCATION_TYPES)}",
            )
        for column in ("facing_from", "facing_count"):
            if p[column] is not None and p[column] < 1:
                faults.add("V-44", "planogram.csv", line, f"{column} must be at least 1")
        if None not in (p["shelf_no"], p["facing_from"], p["facing_count"]):
            shelves[(p["node_id"], p["shelf_no"])].append(
                (p["facing_from"], p["facing_count"], line, p["sku"])
            )
    for (node, shelf), spans in shelves.items():
        for i, (start, count, line, sku) in enumerate(spans):
            for other_start, other_count, other_line, other_sku in spans[:i]:
                if start < other_start + other_count and other_start < start + count:
                    faults.add(
                        "V-45",
                        "planogram.csv",
                        line,
                        f"{sku} overlaps {other_sku} (row {other_line}) on {node} shelf {shelf}",
                    )

    _nodes_file(t["map_nodes.csv"], faults)

    seen_connector = {}
    for line, e in t["map_edges.csv"]:
        if e["weight_m"] is not None and e["weight_m"] <= 0:
            faults.add("V-61", "map_edges.csv", line, f"weight_m {e['weight_m']} must be above 0")
        if e["penalty_m"] is not None and e["penalty_m"] < 0:
            faults.add("V-61", "map_edges.csv", line, f"penalty_m {e['penalty_m']} is negative")
        if e["kind"] in ("stairs", "escalator") and e["step_free"]:
            faults.add("V-62", "map_edges.csv", line, f"{e['kind']} cannot be step_free")
        if e["kind"] == "stairs" and e["trolley"]:
            faults.add("V-62", "map_edges.csv", line, "stairs cannot take a trolley")
        if e["from_node"] == e["to_node"]:
            faults.add("V-64", "map_edges.csv", line, f"edge joins {e['from_node']} to itself")
        k = (e["from_node"], e["to_node"], e["kind"])
        if k in seen_connector:
            faults.add(
                "V-65",
                "map_edges.csv",
                line,
                f"same {e['kind']} between {k[0]} and {k[1]} as row {seen_connector[k]}",
            )
        seen_connector.setdefault(k, line)


def _store_file(folder: Path, rows, faults) -> None:
    values = {r["key"]: (line, r["value"]) for line, r in rows}
    keys = [r["key"] for _, r in rows]
    missing = [k for k in STORE_KEYS if k not in values]
    unknown = [k for k in keys if k not in STORE_KEYS]
    if missing or unknown or len(keys) != len(set(keys)):
        faults.add(
            "V-10",
            "store.csv",
            None,
            f"keys must be exactly {', '.join(STORE_KEYS)} — missing: {missing or 'none'}; unknown: {unknown or 'none'}",
        )
    if "store_id" in values and values["store_id"][1] != folder.name:
        line, value = values["store_id"]
        faults.add(
            "V-11",
            "store.csv",
            line,
            f"store_id {value!r} differs from the folder name {folder.name!r}",
        )
    if "data_provenance" in values and values["data_provenance"][1] != "synthetic":
        line, value = values["data_provenance"]
        faults.add(
            "V-12", "store.csv", line, f"data_provenance is {value!r}; only 'synthetic' is accepted"
        )
    if "planogram_version" in values and _date(values["planogram_version"][1]) is None:
        faults.add(
            "V-12",
            "store.csv",
            values["planogram_version"][0],
            "planogram_version is not an ISO date",
        )
    if "stock_as_of" in values and _timestamp(values["stock_as_of"][1]) is None:
        faults.add(
            "V-12",
            "store.csv",
            values["stock_as_of"][0],
            "stock_as_of is not an ISO 8601 UTC timestamp ending in Z",
        )


def _date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _timestamp(text: str) -> datetime | None:
    if not text.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _products_file(rows, faults) -> None:
    barcodes = {}
    for line, p in rows:
        if p["sku"] is not None and not SKU.fullmatch(p["sku"]):
            faults.add(
                "V-20",
                "products.csv",
                line,
                f"sku {p['sku']!r} must be 7 digits and not begin with 0",
            )
        code = p["barcode"]
        if code is not None:
            if not BARCODE.fullmatch(code):
                faults.add(
                    "V-21", "products.csv", line, f"barcode {code!r} must be exactly 13 digits"
                )
            elif code in barcodes:
                faults.add(
                    "V-21", "products.csv", line, f"barcode {code} repeats row {barcodes[code]}"
                )
            barcodes.setdefault(code, line)
        allergens = p["allergens_contains"]
        if allergens and "none" in allergens:
            faults.add(
                "V-22",
                "products.csv",
                line,
                "allergens_contains combines 'none' with a named allergen",
            )
        price = p["price_gbp"]
        if price is not None and (price < 0 or price.as_tuple().exponent < -2):
            faults.add(
                "V-23",
                "products.csv",
                line,
                f"price_gbp {price} must be 0 or more with at most 2 decimal places",
            )
        pop = p["popularity"]
        if pop is not None and not 0.0 <= pop <= 1.0:
            faults.add(
                "V-23", "products.csv", line, f"popularity {pop} must be between 0.0 and 1.0"
            )


def _nodes_file(rows, faults) -> None:
    name = "map_nodes.csv"
    floor_names = defaultdict(Counter)
    places = {}
    for line, n in rows:
        nt = n["node_type"]
        if nt is None:
            continue
        m = re.fullmatch(NODE_ID[nt], n["node_id"] or "")
        if not m:
            faults.add("V-50", name, line, f"{n['node_id']!r} is not a valid {nt} identifier")
        else:
            level, *rest = (int(g) for g in m.groups())
            agree = level == n["level"]
            if nt in ("rack", "aisle_end"):
                agree &= rest[0] == n["aisle"]
            if nt == "rack":
                agree &= rest[1] == n["rack"]
            if not agree:
                faults.add(
                    "V-50",
                    name,
                    line,
                    f"{n['node_id']} disagrees with its level, aisle or rack columns",
                )
        if nt in AISLE_REQUIRED and n["aisle"] is None:
            faults.add("V-06", name, line, f"aisle is required on a {nt}")
        if nt not in AISLE_REQUIRED | AISLE_OPTIONAL and n["aisle"] is not None:
            faults.add("V-06", name, line, f"aisle must be empty on a {nt}")
        if (nt == "rack") != (n["rack"] is not None):
            faults.add(
                "V-06", name, line, f"rack must be {'set' if nt == 'rack' else 'empty'} on a {nt}"
            )
        if nt == "rack" and (n["shelf_count"] is None or n["shelf_count"] < 1):
            faults.add("V-55", name, line, "a rack needs shelf_count of at least 1")
        if nt != "rack" and n["shelf_count"] is not None:
            faults.add("V-55", name, line, f"shelf_count must be empty on a {nt}")
        if n["floor_name"] is not None and n["level"] is not None:
            floor_names[n["level"]][n["floor_name"]] += 1
        place = (n["level"], n["x_m"], n["y_m"])
        if place in places:
            faults.add("V-56", name, line, f"drawn on the same point as row {places[place]}")
        places.setdefault(place, line)
    for line, n in rows:
        names = floor_names.get(n["level"])
        if names and len(names) > 1 and n["floor_name"] != names.most_common(1)[0][0]:
            faults.add(
                "V-51",
                name,
                line,
                f"floor_name {n['floor_name']!r} differs from the rest of level {n['level']}",
            )

    levels = sorted({n["level"] for _, n in rows if n["level"] is not None})
    if levels and levels != list(range(levels[-1] + 1)):
        faults.add("V-52", name, None, f"levels {levels} are not contiguous from 0")
    entrances = [n for _, n in rows if n["node_type"] == "entrance"]
    if len(entrances) != 1 or entrances[0]["level"] != 0:
        faults.add(
            "V-53", name, None, f"needs exactly one entrance on level 0; found {len(entrances)}"
        )
    if not any(n["node_type"] == "till" and n["level"] == 0 for _, n in rows):
        faults.add("V-54", name, None, "needs at least one till on level 0")


# ── stage 3 · across files ──────────────────────────────────────────────────────────────────


def _across(t: dict[str, list[Row]], faults: _Faults) -> None:
    skus = {p["sku"] for _, p in t["products.csv"]}
    stocked = {s["sku"] for _, s in t["stock.csv"]}
    nodes = {n["node_id"]: n for _, n in t["map_nodes.csv"]}

    for line, s in t["stock.csv"]:
        if s["sku"] not in skus:
            faults.add("V-30", "stock.csv", line, f"sku {s['sku']} is not in products.csv")
    unstocked = sorted(skus - stocked)
    if unstocked:
        faults.add("V-32", "stock.csv", None, f"no stock row for {', '.join(unstocked)}")

    for line, p in t["planogram.csv"]:
        if p["sku"] not in skus:
            faults.add("V-40", "planogram.csv", line, f"sku {p['sku']} is not in products.csv")
        node = nodes.get(p["node_id"])
        if node is None:
            faults.add(
                "V-41", "planogram.csv", line, f"node {p['node_id']} is not in map_nodes.csv"
            )
            continue
        allowed = COMPATIBLE.get(p["location_type"], {})
        if node["node_type"] not in allowed:
            faults.add(
                "V-46",
                "planogram.csv",
                line,
                f"{p['location_type']} cannot sit on a {node['node_type']} ({p['node_id']})",
            )
            continue
        shelved = [p[c] is not None for c in SHELF_COLUMNS]
        if allowed[node["node_type"]] and not all(shelved):
            faults.add(
                "V-46",
                "planogram.csv",
                line,
                f"{p['location_type']} on a {node['node_type']} needs shelf_no, facing_from and facing_count",
            )
        if not allowed[node["node_type"]] and any(shelved):
            faults.add(
                "V-46",
                "planogram.csv",
                line,
                f"{p['location_type']} on a {node['node_type']} has no shelf or facing",
            )
        if (
            p["shelf_no"] is not None
            and node["shelf_count"] is not None
            and p["shelf_no"] > node["shelf_count"]
        ):
            faults.add(
                "V-43",
                "planogram.csv",
                line,
                f"shelf {p['shelf_no']} is above {p['node_id']}'s {node['shelf_count']} shelves",
            )

    for line, e in t["map_edges.csv"]:
        ends = [nodes.get(e["from_node"]), nodes.get(e["to_node"])]
        if None in ends:
            gone = [
                n
                for n, found in zip((e["from_node"], e["to_node"]), ends, strict=True)
                if found is None
            ]
            faults.add("V-60", "map_edges.csv", line, f"unknown node {', '.join(gone)}")
            continue
        a, b = ends
        if e["kind"] in VERTICAL:
            same_core = a["node_id"].split("-", 1)[1] == b["node_id"].split("-", 1)[1]
            if not (
                a["node_type"] == b["node_type"] == "core"
                and same_core
                and a["level"] != b["level"]
            ):
                faults.add(
                    "V-63",
                    "map_edges.csv",
                    line,
                    f"a {e['kind']} must join the same core on two levels, not {a['node_id']} and {b['node_id']}",
                )
        elif a["level"] != b["level"]:
            faults.add(
                "V-63",
                "map_edges.csv",
                line,
                f"an {e['kind']} edge cannot change level ({a['node_id']} → {b['node_id']})",
            )


# ── stage 4 · the open graph ────────────────────────────────────────────────────────────────


def _reach(start: str, arcs: dict[str, set[str]]) -> set[str]:
    seen, queue = {start}, deque([start])
    while queue:
        for nxt in arcs[queue.popleft()]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _arcs(open_nodes, edges, step_free_only=False):
    forward, backward = defaultdict(set), defaultdict(set)
    for e in edges:
        if not e["is_open"] or (step_free_only and not e["step_free"]):
            continue
        a, b = e["from_node"], e["to_node"]
        if a not in open_nodes or b not in open_nodes:
            continue
        pairs = [(a, b), (b, a)] if e["bidirectional"] else [(a, b)]
        for x, y in pairs:
            forward[x].add(y)
            backward[y].add(x)
    return forward, backward


def _sample(ids) -> str:
    ids = sorted(ids)
    return ", ".join(ids[:5]) + (f" and {len(ids) - 5} more" if len(ids) > 5 else "")


def _graph(t: dict[str, list[Row]], faults: _Faults) -> None:
    name = "map_edges.csv"
    nodes = {n["node_id"]: n for _, n in t["map_nodes.csv"] if n["is_open"]}
    edges = [e for _, e in t["map_edges.csv"]]
    entrance = (
        next(i for i, n in nodes.items() if n["node_type"] == "entrance")
        if any(n["node_type"] == "entrance" for n in nodes.values())
        else None
    )
    if entrance is None:
        faults.add("V-71", name, None, "the entrance is closed, so no level can be reached")
        return

    fwd, back = _arcs(nodes, edges)
    reached, reaching = _reach(entrance, fwd), _reach(entrance, back)
    if reached != set(nodes) or reaching != set(nodes):
        parts = []
        if set(nodes) - reached:
            parts.append(f"{_sample(set(nodes) - reached)} cannot be reached from {entrance}")
        if set(nodes) - reaching:
            parts.append(f"{_sample(set(nodes) - reaching)} cannot get back to {entrance}")
        faults.add("V-70", name, None, "the store is not strongly connected: " + "; ".join(parts))

    for level in sorted({n["level"] for n in nodes.values()}):
        if not any(nodes[i]["level"] == level for i in reached):
            faults.add("V-71", name, None, f"level {level} cannot be reached from {entrance}")

    sf_fwd, sf_back = _arcs(nodes, edges, step_free_only=True)
    sf_reached, sf_reaching = _reach(entrance, sf_fwd), _reach(entrance, sf_back)
    if sf_reached != set(nodes) or sf_reaching != set(nodes):
        cut = (set(nodes) - sf_reached) | (set(nodes) - sf_reaching)
        faults.add(
            "V-72", name, None, f"the step-free routes do not join every point: {_sample(cut)}"
        )

    placed = {p["node_id"] for _, p in t["planogram.csv"]} & set(nodes)
    if placed - reached:
        faults.add(
            "V-73",
            name,
            None,
            f"products sit on points the entrance cannot reach: {_sample(placed - reached)}",
        )

    for till in sorted(i for i, n in nodes.items() if n["node_type"] == "till"):
        cut_off = set(nodes) - _reach(till, back)
        if cut_off:
            levels = sorted({nodes[i]["level"] for i in cut_off})
            faults.add(
                "V-74",
                name,
                None,
                f"{till} cannot be reached from level {', '.join(map(str, levels))}",
            )


# ── warnings ────────────────────────────────────────────────────────────────────────────────


def _warnings(t: dict[str, list[Row]]) -> list[Fault]:
    out = _Faults()
    products = {p["sku"]: (line, p) for line, p in t["products.csv"]}
    nodes = {n["node_id"]: (line, n) for line, n in t["map_nodes.csv"]}
    placed_skus = {p["sku"] for _, p in t["planogram.csv"]}
    placed_nodes = {p["node_id"] for _, p in t["planogram.csv"]}

    aisles = defaultdict(set)
    for _, p in t["planogram.csv"]:
        _, node = nodes[p["node_id"]]
        if node["node_type"] == "rack":
            aisles[products[p["sku"]][1]["aisle_category"]].add((node["level"], node["aisle"]))
    for category, where in sorted(aisles.items()):
        if len(where) > 1:
            spots = ", ".join(f"F{lv}-A{a:02}" for lv, a in sorted(where))
            out.add(
                "W-01",
                "planogram.csv",
                None,
                f"category {category!r} sits on racks in aisles {spots}",
            )

    for line, s in t["stock.csv"]:
        if s["ranged"] and s["shelf_qty"] > 0 and s["sku"] not in placed_skus:
            out.add(
                "W-02",
                "stock.csv",
                line,
                f"{s['sku']} is ranged and in stock but has no placement — its location will read as unknown",
            )

    for line, e in t["map_edges.csv"]:
        if e["kind"] in ("aisle", "corridor"):
            a, b = nodes[e["from_node"]][1], nodes[e["to_node"]][1]
            straight = math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])
            if straight > 0 and abs(e["weight_m"] - straight) / straight > 0.5:
                out.add(
                    "W-03",
                    "map_edges.csv",
                    line,
                    f"weight {e['weight_m']} m against {straight:.1f} m drawn",
                )

    for line, n in t["map_nodes.csv"]:
        if n["node_type"] == "rack" and n["node_id"] not in placed_nodes:
            out.add("W-04", "map_nodes.csv", line, f"rack {n['node_id']} has no placements")

    for column in DIET_COLUMNS:
        empty = sum(1 for _, p in products.values() if p[column] is None)
        if empty * 2 > len(products):
            out.add(
                "W-05",
                "products.csv",
                None,
                f"{column} is unknown for {empty} of {len(products)} products",
            )
    return list(out)


# ── assembly ────────────────────────────────────────────────────────────────────────────────


def load_store(folder: Path) -> Store:
    """Load and validate one store folder. Raises StoreDataError naming every fault found."""
    folder = Path(folder)
    faults = _Faults()
    t = _parse(folder, faults)
    stages = (
        lambda: _within(folder, t, faults),
        lambda: _across(t, faults),
        lambda: _graph(t, faults),
    )
    for stage in stages:
        if faults:
            break
        stage()
    if faults:
        raise StoreDataError(list(faults))

    info = {r["key"]: r["value"] for _, r in t["store.csv"]}
    return Store(
        info=StoreInfo(
            store_id=info["store_id"],
            store_name=info["store_name"],
            data_provenance=info["data_provenance"],
            planogram_version=_date(info["planogram_version"]),
            stock_as_of=_timestamp(info["stock_as_of"]),
        ),
        products={
            p["sku"]: Product(**{**p, "price_gbp": float(p["price_gbp"])})
            for _, p in t["products.csv"]
        },
        stock={s["sku"]: StockPosition(**s) for _, s in t["stock.csv"]},
        placements=tuple(Placement(**p) for _, p in t["planogram.csv"]),
        nodes={n["node_id"]: MapNode(**n) for _, n in t["map_nodes.csv"]},
        edges=tuple(MapEdge(**e) for _, e in t["map_edges.csv"]),
        warnings=tuple(_warnings(t)),
    )
