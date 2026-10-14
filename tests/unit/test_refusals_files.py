COKE = {"sku": "7123456"}
COKE_HOME = {"sku": "7123456", "location_type": "HOME"}
FRONT_STAIRS = {"kind": "stairs", "from_node": "F0-CORE-FRONT"}


class TestStoreFile:
    """AC-14, NFR-07 — store.csv refusals."""

    def test_v_10_missing_key(self, store):
        store.drop("store.csv", {"key": "store_name"})
        store.assert_refused("V-10", "store.csv")

    def test_v_10_unknown_key(self, store):
        store.add("store.csv", {"key": "store_colour", "value": "orange"})
        store.assert_refused("V-10", "store.csv")

    def test_v_11_store_id_differs_from_folder(self, store):
        row = store.edit("store.csv", {"key": "store_id"}, value="SBY-DEMO-002")
        store.assert_refused("V-11", "store.csv", row=row)

    def test_v_12_provenance_not_synthetic(self, store):
        row = store.edit("store.csv", {"key": "data_provenance"}, value="live")
        store.assert_refused("V-12", "store.csv", row=row)

    def test_v_12_timestamp_not_iso(self, store):
        row = store.edit("store.csv", {"key": "stock_as_of"}, value="yesterday")
        store.assert_refused("V-12", "store.csv", row=row)


class TestProductsFile:
    """AC-14, NFR-07 — products.csv refusals."""

    def test_v_20_sku_with_leading_zero(self, store):
        row = store.edit("products.csv", COKE, sku="0123456")
        store.assert_refused("V-20", "products.csv", row=row)

    def test_v_20_sku_of_six_digits(self, store):
        row = store.edit("products.csv", COKE, sku="712345")
        store.assert_refused("V-20", "products.csv", row=row)

    def test_v_21_barcode_in_scientific_notation(self, store):
        row = store.edit("products.csv", COKE, barcode="2.04063E+12")
        store.assert_refused("V-21", "products.csv", row=row)

    def test_v_21_barcode_repeated(self, store):
        rows = store.rows("products.csv")
        first = next(r for r in rows if r["barcode"])
        row = store.edit("products.csv", COKE, barcode=first["barcode"])
        store.assert_refused("V-21", "products.csv", row=row)

    def test_v_21_barcode_with_a_failed_check_digit(self, store):
        code = next(r["barcode"] for r in store.rows("products.csv") if r["sku"] == COKE["sku"])
        bad = code[:-1] + str((int(code[-1]) + 1) % 10)
        row = store.edit("products.csv", COKE, barcode=bad)
        store.assert_refused("V-21", "products.csv", row=row)

    def test_v_22_none_alongside_an_allergen(self, store):
        row = store.edit("products.csv", COKE, allergens_contains="none|milk")
        store.assert_refused("V-22", "products.csv", row=row)

    def test_v_23_negative_price(self, store):
        row = store.edit("products.csv", COKE, price_gbp="-1.00")
        store.assert_refused("V-23", "products.csv", row=row)

    def test_v_23_price_with_three_decimals(self, store):
        row = store.edit("products.csv", COKE, price_gbp="1.655")
        store.assert_refused("V-23", "products.csv", row=row)

    def test_v_23_popularity_out_of_range(self, store):
        row = store.edit("products.csv", COKE, popularity="1.5")
        store.assert_refused("V-23", "products.csv", row=row)


class TestStockFile:
    """AC-14, NFR-07 — stock.csv refusals and its total join to the catalogue."""

    def test_v_30_stock_row_for_unknown_sku(self, store):
        store.add("stock.csv", {"sku": "9999999", "ranged": "true", "shelf_qty": "3"})
        store.assert_refused("V-30", "stock.csv")

    def test_v_31_not_ranged_but_stocked(self, store):
        row = store.edit("stock.csv", COKE, ranged="false", shelf_qty="5")
        store.assert_refused("V-31", "stock.csv", row=row)

    def test_v_32_product_with_no_stock_row(self, store):
        store.drop("stock.csv", COKE)
        err = store.assert_refused("V-32", "stock.csv")
        assert "7123456" in str(err)

    def test_v_33_negative_quantity(self, store):
        row = store.edit("stock.csv", COKE, shelf_qty="-1")
        store.assert_refused("V-33", "stock.csv", row=row)


class TestPlanogramFile:
    """AC-14, NFR-07 — planogram.csv refusals."""

    def test_v_40_placement_for_unknown_sku(self, store):
        row = store.edit("planogram.csv", COKE_HOME, sku="9999999")
        store.assert_refused("V-40", "planogram.csv", row=row)

    def test_v_41_placement_on_unknown_node(self, store):
        row = store.edit("planogram.csv", COKE_HOME, node_id="F1-A07-R09")
        store.assert_refused("V-41", "planogram.csv", row=row)

    def test_v_42_unknown_location_type(self, store):
        row = store.edit("planogram.csv", COKE_HOME, location_type="SHELF")
        store.assert_refused("V-42", "planogram.csv", row=row)

    def test_v_43_shelf_above_the_rack(self, store):
        row = store.edit("planogram.csv", COKE_HOME, shelf_no="9")
        store.assert_refused("V-43", "planogram.csv", row=row)

    def test_v_44_zero_facings(self, store):
        row = store.edit("planogram.csv", COKE_HOME, facing_count="0")
        store.assert_refused("V-44", "planogram.csv", row=row)

    def test_v_45_overlapping_facings(self, store):
        rows = store.rows("planogram.csv")
        other = next(r["sku"] for r in rows if r["sku"] != "7123456")
        row = store.add("planogram.csv", {
            "sku": other, "node_id": "F1-A07-R03", "location_type": "HOME",
            "shelf_no": "2", "facing_from": "2", "facing_count": "2", "seasonal": "false",
        })  # fmt: skip
        store.assert_refused("V-45", "planogram.csv", row=row)

    def test_v_46_counter_with_a_shelf(self, store):
        row = store.edit("planogram.csv", {"location_type": "COUNTER"}, shelf_no="1")
        store.assert_refused("V-46", "planogram.csv", row=row)

    def test_v_46_home_placement_on_an_aisle_end(self, store):
        row = store.edit("planogram.csv", COKE_HOME, node_id="F1-A07-S")
        store.assert_refused("V-46", "planogram.csv", row=row)


class TestMapNodesFile:
    """AC-14, NFR-07 — map_nodes.csv refusals."""

    def test_v_50_identifier_disagrees_with_its_columns(self, store):
        row = store.edit("map_nodes.csv", {"node_id": "F1-A07-R03"}, rack="4")
        store.assert_refused("V-50", "map_nodes.csv", row=row)

    def test_v_51_floor_name_drifts_within_a_level(self, store):
        row = store.edit("map_nodes.csv", {"node_id": "F1-A07-R03"}, floor_name="Groceries")
        store.assert_refused("V-51", "map_nodes.csv", row=row)

    def test_v_52_levels_not_contiguous(self, store):
        for name in ("map_nodes.csv", "map_edges.csv", "planogram.csv"):
            path = store.path / name
            path.write_text(path.read_text().replace("F2-", "F3-"))
        store.edit_all("map_nodes.csv", {"level": "2"}, level="3")
        store.assert_refused("V-52", "map_nodes.csv")

    def test_v_53_no_entrance(self, store):
        store.drop("map_nodes.csv", {"node_id": "F0-ENTRANCE"})
        store.assert_refused("V-53", "map_nodes.csv")

    def test_v_54_no_till(self, store):
        rows = [r for r in store.rows("map_nodes.csv") if r["node_type"] != "till"]
        store.write("map_nodes.csv", rows)
        store.assert_refused("V-54", "map_nodes.csv")

    def test_v_55_rack_with_no_shelves(self, store):
        row = store.edit("map_nodes.csv", {"node_id": "F0-A01-R01"}, shelf_count="0")
        store.assert_refused("V-55", "map_nodes.csv", row=row)

    def test_v_55_shelf_count_on_an_aisle_end(self, store):
        row = store.edit("map_nodes.csv", {"node_id": "F0-A01-N"}, shelf_count="3")
        store.assert_refused("V-55", "map_nodes.csv", row=row)

    def test_v_56_two_nodes_drawn_on_one_point(self, store):
        r2 = next(r for r in store.rows("map_nodes.csv") if r["node_id"] == "F0-A01-R02")
        row = store.edit("map_nodes.csv", {"node_id": "F0-A01-R01"}, y_m=r2["y_m"])
        err = store.assert_refused("V-56", "map_nodes.csv")  # reported on one row of the pair,
        assert f"row {row}" in str(err)  # naming the other


class TestMapEdgesFile:
    """AC-14, NFR-07 — map_edges.csv refusals."""

    def test_v_60_edge_to_unknown_node(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, to_node="F0-A01-R09")
        store.assert_refused("V-60", "map_edges.csv", row=row)

    def test_v_61_zero_weight(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, weight_m="0.0")
        store.assert_refused("V-61", "map_edges.csv", row=row)

    def test_v_61_negative_penalty(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, penalty_m="-1.0")
        store.assert_refused("V-61", "map_edges.csv", row=row)

    def test_v_62_stairs_marked_step_free(self, store):
        row = store.edit("map_edges.csv", FRONT_STAIRS, step_free="true")
        store.assert_refused("V-62", "map_edges.csv", row=row)

    def test_v_63_corridor_through_a_ceiling(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, to_node="F1-A01-N")
        store.assert_refused("V-63", "map_edges.csv", row=row)

    def test_v_63_lift_arriving_at_the_other_core(self, store):
        row = store.edit("map_edges.csv", {"kind": "lift", "from_node": "F0-CORE-FRONT"},
                         to_node="F1-CORE-REAR")  # fmt: skip
        store.assert_refused("V-63", "map_edges.csv", row=row)

    def test_v_64_self_loop(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, to_node="F0-A01-N")
        store.assert_refused("V-64", "map_edges.csv", row=row)

    def test_v_65_two_indistinguishable_connectors(self, store):
        stairs = next(r for r in store.rows("map_edges.csv") if r["kind"] == "stairs")
        row = store.add("map_edges.csv", {**stairs, "edge_id": "E0999"})
        store.assert_refused("V-65", "map_edges.csv", row=row)
