COKE = {"sku": "7123456"}


class TestFormatRefusals:
    """AC-14, NFR-07 — format faults are refused at load, naming file, row and rule."""

    def test_v_01_unknown_and_missing_column(self, store):
        rows = store.rows("products.csv")
        header = ["brnd" if h == "brand" else h for h in store.header("products.csv")]
        store.write("products.csv", [{("brnd" if k == "brand" else k): v for k, v in r.items()}
                                     for r in rows], header)  # fmt: skip
        err = store.assert_refused("V-01", "products.csv")
        assert "brnd" in str(err) and "brand" in str(err)

    def test_v_01_duplicate_column(self, store):
        path = store.path / "stock.csv"
        lines = path.read_text().splitlines()
        path.write_text(
            "\n".join([lines[0] + ",ranged"] + [ln + ",true" for ln in lines[1:]]) + "\n"
        )
        store.assert_refused("V-01", "stock.csv")

    def test_v_02_byte_order_mark(self, store):
        path = store.path / "stock.csv"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        store.assert_refused("V-02", "stock.csv")

    def test_v_02_not_utf8(self, store):
        path = store.path / "products.csv"
        path.write_bytes(path.read_bytes().replace(b"Rose", b"Ros\xe9"))
        store.assert_refused("V-02", "products.csv")

    def test_v_03_duplicate_primary_key(self, store):
        rows = store.rows("map_edges.csv")
        rows.append(dict(rows[0]))
        store.write("map_edges.csv", rows)
        store.assert_refused("V-03", "map_edges.csv", row=len(rows) + 1)

    def test_v_04_boolean_spelt_differently(self, store):
        row = store.edit("products.csv", COKE, diet_vegan="TRUE")
        store.assert_refused("V-04", "products.csv", row=row)

    def test_v_04_two_state_boolean_left_empty(self, store):
        row = store.edit("stock.csv", COKE, ranged="")
        store.assert_refused("V-04", "stock.csv", row=row)

    def test_v_05_empty_list_segment(self, store):
        row = store.edit("products.csv", COKE, synonyms="coke||cola")
        store.assert_refused("V-05", "products.csv", row=row)

    def test_v_05_trailing_delimiter(self, store):
        row = store.edit("products.csv", COKE, allergens_contains="milk|")
        store.assert_refused("V-05", "products.csv", row=row)

    def test_v_06_required_cell_empty(self, store):
        row = store.edit("products.csv", COKE, name="")
        store.assert_refused("V-06", "products.csv", row=row)

    def test_v_06_file_with_no_rows(self, store):
        store.write("stock.csv", [])
        store.assert_refused("V-06", "stock.csv")

    def test_v_06_an_empty_planogram_is_allowed(self, store):
        store.write("planogram.csv", [])
        loaded = store.load()  # legal, if suspicious: every rack is empty
        assert loaded.placements == ()
        assert "W-04" in {w.rule for w in loaded.warnings}

    def test_v_07_number_with_text(self, store):
        row = store.edit("stock.csv", COKE, shelf_qty="14 units")
        store.assert_refused("V-07", "stock.csv", row=row)

    def test_v_07_unknown_node_type(self, store):
        row = store.edit("map_nodes.csv", {"node_id": "F0-X01"}, node_type="hallway")
        store.assert_refused("V-07", "map_nodes.csv", row=row)

    def test_v_07_malformed_edge_id(self, store):
        row = store.edit("map_edges.csv", {"edge_id": "E0001"}, edge_id="E1")
        store.assert_refused("V-07", "map_edges.csv", row=row)
