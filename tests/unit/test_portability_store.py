"""C-04, A-03 — the portability store: same catalogue and stock, a differently shaped map."""

import csv
import io
from collections import Counter
from pathlib import Path

from datagen.build import DEFAULT_SEED, build_store
from validation import load_store

REPO = Path(__file__).resolve().parents[2]
PORT = REPO / "data" / "SBY-PORT-002"


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


class TestPortabilityStore:
    """C-04, A-03 — generated, committed, and shaped differently from the demo store."""

    def test_the_committed_folder_is_the_generator_output(self):
        fresh = build_store(DEFAULT_SEED, store="port")
        for name, text in fresh.items():
            assert (PORT / name).read_bytes() == text.encode("utf-8"), (
                f"{name} — run: uv run python -m datagen --store port"
            )

    def test_same_catalogue_and_stock_as_the_demo_store(self):
        demo, port = build_store(DEFAULT_SEED), build_store(DEFAULT_SEED, store="port")
        assert port["products.csv"] == demo["products.csv"]
        assert port["stock.csv"] == demo["stock.csv"]
        assert port["planogram.csv"] != demo["planogram.csv"]

    def test_a_03_two_floors_five_rack_aisles_and_the_sizes_in_the_schema(self):
        files = build_store(DEFAULT_SEED, store="port")
        nodes, edges = rows(files["map_nodes.csv"]), rows(files["map_edges.csv"])
        assert {n["level"] for n in nodes} == {"0", "1"}
        assert (len(nodes), len(edges)) == (125, 140)
        racks_per_aisle = Counter(
            (n["level"], n["aisle"]) for n in nodes if n["node_type"] == "rack"
        )
        assert set(racks_per_aisle.values()) == {5} and len(racks_per_aisle) == 15
        assert sum(n["node_type"] == "till" for n in nodes) == 4

    def test_racks_hold_several_products_on_different_shelves(self):
        placements = rows(build_store(DEFAULT_SEED, store="port")["planogram.csv"])
        per_rack = Counter(p["node_id"] for p in placements if p["shelf_no"])
        assert max(per_rack.values()) >= 2

    def test_it_loads_with_only_the_deliberate_warning(self):
        store = load_store(PORT)
        assert store.info.store_id == "SBY-PORT-002"
        assert [w.rule for w in store.warnings] == ["W-02"]
