def rules(loaded):
    return [w.rule for w in loaded.warnings]


class TestWarnings:
    """AC-14, NFR-07 — suspicious but legitimate patterns load and are reported."""

    def test_the_demo_store_raises_only_its_deliberate_w_02(self, store):
        loaded = store.load()
        assert rules(loaded) == ["W-02"]
        lime = next(p for p in loaded.products.values() if p.name == "Sparkling Water Lime")
        assert lime.sku in str(loaded.warnings[0])

    def test_w_01_category_split_across_aisles(self, store):
        store.edit("planogram.csv", {"node_id": "F0-A01-R01"},
                   node_id="F0-A02-R06", facing_from="5")  # fmt: skip
        assert "W-01" in rules(store.load())

    def test_w_02_stocked_and_ranged_with_no_placement(self, store):
        assert "W-02" in rules(store.load())

    def test_w_03_weight_far_from_the_drawn_distance(self, store):
        store.edit("map_edges.csv", {"edge_id": "E0002"}, weight_m="9.6")
        assert "W-03" in rules(store.load())

    def test_w_04_rack_with_no_placements(self, store):
        store.drop("planogram.csv", {"node_id": "F0-A01-R06"})
        assert "W-04" in rules(store.load())

    def test_w_05_dietary_column_mostly_unknown(self, store):
        store.edit_all("products.csv", {}, diet_halal="")
        assert "W-05" in rules(store.load())
