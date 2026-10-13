UPPER_VERTICALS = ("F1-CORE-FRONT", "F1-CORE-REAR")


def one_way_out_of(store, node_id):
    """Make the only edge touching ``node_id`` leave it and never return."""
    edges = store.rows("map_edges.csv")
    (edge,) = [e for e in edges if node_id in (e["from_node"], e["to_node"])]
    assert edge["from_node"] == node_id
    return store.edit("map_edges.csv", {"edge_id": edge["edge_id"]}, bidirectional="false")


def close_upper_connectors(store, kinds):
    for core in UPPER_VERTICALS:
        for kind in kinds:
            store.edit("map_edges.csv", {"from_node": core, "kind": kind}, is_open="false")


class TestGraphRefusals:
    """AC-14, NFR-07 — the assembled open graph is walkable, step-free included."""

    def test_v_70_a_node_that_cannot_be_reached(self, store):
        one_way_out_of(store, "F0-CTR-01")
        store.assert_refused("V-70", "map_edges.csv")

    def test_v_71_a_floor_with_no_working_connector(self, store):
        close_upper_connectors(store, ("lift", "stairs"))
        err = store.assert_refused("V-71", "map_edges.csv")
        assert "level 2" in str(err)

    def test_v_72_step_free_graph_split_while_stairs_still_join_it(self, store):
        close_upper_connectors(store, ("lift",))
        err = store.refusal()
        assert err.rules == {"V-72"}

    def test_v_73_a_placement_on_an_unreachable_node(self, store):
        one_way_out_of(store, "F0-CTR-01")
        err = store.assert_refused("V-73", "map_edges.csv")
        assert "F0-CTR-01" in str(err)

    def test_v_73_a_closed_node_is_not_an_orphan(self, store):
        store.edit("map_nodes.csv", {"node_id": "F0-CTR-01"}, is_open="false")
        store.load()  # EC-32: closure is intentional, so the store still loads

    def test_v_74_a_till_that_cannot_be_reached(self, store):
        one_way_out_of(store, "F0-TILL-03")
        err = store.assert_refused("V-74", "map_edges.csv")
        assert "F0-TILL-03" in str(err)


class TestStages:
    """CONST-VI — a store loads completely or not at all, and faults arrive a stage at a time."""

    def test_the_demo_store_loads(self, store):
        loaded = store.load()
        assert len(loaded.products) == 180 and len(loaded.nodes) == 314

    def test_every_fault_in_a_stage_is_reported_together(self, store):
        store.edit("products.csv", {"sku": "7123456"}, price_gbp="-1.00")
        store.edit("stock.csv", {"sku": "7123456"}, shelf_qty="-1")
        assert {"V-23", "V-33"} <= store.refusal().rules

    def test_a_later_stage_does_not_run_after_a_failed_one(self, store):
        store.edit("products.csv", {"sku": "7123456"}, price_gbp="-1.00")  # within-file
        store.edit("planogram.csv", {"sku": "7123456"}, node_id="F1-A07-R09")  # referential
        assert store.refusal().rules == {"V-23"}
