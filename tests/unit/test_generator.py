import csv
import io
from pathlib import Path

from datagen.build import DEFAULT_SEED, FILES, build_store

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "data" / "SBY-DEMO-001"

PRIMARY_KEYS = {
    "store.csv": ("key",),
    "products.csv": ("sku",),
    "stock.csv": ("sku",),
    "planogram.csv": ("sku", "node_id", "shelf_no", "facing_from"),
    "map_nodes.csv": ("node_id",),
    "map_edges.csv": ("edge_id",),
}


def rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


class TestGenerator:
    """C-04 — the seeded generator writes the synthetic demo store the schema describes."""

    def test_the_same_seed_gives_identical_files(self):
        assert build_store(DEFAULT_SEED) == build_store(DEFAULT_SEED)

    def test_a_different_seed_changes_the_seeded_details(self):
        assert build_store(DEFAULT_SEED)["products.csv"] != build_store(1)["products.csv"]

    def test_c_04_the_store_declares_itself_synthetic(self):
        store = {r["key"]: r["value"] for r in rows(build_store(DEFAULT_SEED)["store.csv"])}
        assert store["data_provenance"] == "synthetic"
        assert store["store_id"] == "SBY-DEMO-001"

    def test_a_03_a_04_sizes_match_the_schema(self):
        files = build_store(DEFAULT_SEED)
        counts = {name: len(rows(text)) for name, text in files.items()}
        assert counts["store.csv"] == 5
        assert counts["products.csv"] == counts["stock.csv"] == 180
        assert 230 <= counts["planogram.csv"] <= 270
        assert counts["map_nodes.csv"] == 314
        assert counts["map_edges.csv"] == 352
        levels = {r["level"] for r in rows(files["map_nodes.csv"])}
        assert levels == {"0", "1", "2"}

    def test_every_demo_edge_is_bidirectional(self):
        edges = rows(build_store(DEFAULT_SEED)["map_edges.csv"])
        assert {e["bidirectional"] for e in edges} == {"true"}

    def test_v_02_v_03_files_are_utf8_lf_and_sorted_by_primary_key(self):
        for name, text in build_store(DEFAULT_SEED).items():
            assert not text.startswith("﻿") and "\r" not in text, name
            key = PRIMARY_KEYS[name]
            if name == "store.csv":
                continue  # key–value file: keys in schema order, not sorted
            keys = [tuple(r[k] for k in key) for r in rows(text)]
            assert keys == sorted(keys), f"{name} is not sorted by {key}"
            assert len(keys) == len(set(keys)), f"{name} repeats a primary key"

    def test_the_committed_demo_store_is_the_generator_output(self):
        fresh = build_store(DEFAULT_SEED)
        assert set(FILES) == {p.name for p in DEMO.iterdir()}
        for name in FILES:
            assert (DEMO / name).read_bytes() == fresh[name].encode("utf-8"), (
                f"{name} differs — run: uv run python -m datagen"
            )
