"""A-03, AC-36 — the city flagship: the demo catalogue in a five-floor building."""

import csv
import io
from collections import Counter
from pathlib import Path

from datagen.build import DEFAULT_SEED, build_store
from validation import load_store

REPO = Path(__file__).resolve().parents[2]
CITY = REPO / "data" / "SBY-CITY-003"


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


class TestCityStore:
    """A-03, AC-36, FR-25 — generated, committed, five floors, its own stock."""

    def test_the_committed_folder_is_the_generator_output(self):
        fresh = build_store(DEFAULT_SEED, store="city")
        for name, text in fresh.items():
            assert (CITY / name).read_bytes() == text.encode("utf-8"), (
                f"{name} — run: uv run python -m datagen --store city"
            )

    def test_a_03_five_floors_and_both_cores_reach_every_one(self):
        files = build_store(DEFAULT_SEED, store="city")
        nodes, edges = rows(files["map_nodes.csv"]), rows(files["map_edges.csv"])
        assert {n["level"] for n in nodes} == {"0", "1", "2", "3", "4"}
        lifts = Counter(e["kind"] for e in edges if e["kind"] in ("lift", "stairs"))
        assert lifts == {"lift": 8, "stairs": 8}  # two cores, four spans each
        assert sum(n["node_type"] == "till" for n in nodes) == 6

    def test_same_catalogue_its_own_shelf_quantities(self):
        demo, city = build_store(DEFAULT_SEED), build_store(DEFAULT_SEED, store="city")
        assert city["products.csv"] == demo["products.csv"]
        d = {r["sku"]: r for r in rows(demo["stock.csv"])}
        c = {r["sku"]: r for r in rows(city["stock.csv"])}
        assert {k: v["ranged"] for k, v in c.items()} == {k: v["ranged"] for k, v in d.items()}
        assert all((c[k]["shelf_qty"] in ("", "0")) == (d[k]["shelf_qty"] in ("", "0")) for k in d)
        assert sum(c[k]["shelf_qty"] != d[k]["shelf_qty"] for k in d) > 50  # another branch

    def test_it_loads_and_every_floor_is_reachable_step_free(self):
        store = load_store(CITY)  # the validator refuses a floor the lifts cannot reach (V-rules)
        assert store.info.store_id == "SBY-CITY-003" and store.info.store_name == "City Flagship"
        assert {n.level for n in store.nodes.values()} == {0, 1, 2, 3, 4}
