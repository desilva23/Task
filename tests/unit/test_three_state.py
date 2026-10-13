COKE = {"sku": "7123456"}


class TestThreeState:
    """CONST-II, NFR-03 — unknown is not false, from the file to the record."""

    def test_the_three_dietary_states_load_as_three_values(self, store):
        store.edit("products.csv", COKE, diet_gluten_free="true", diet_vegan="false", diet_halal="")
        coke = store.load().products["7123456"]
        assert coke.diet_gluten_free is True
        assert coke.diet_vegan is False
        assert coke.diet_halal is None

    def test_allergens_none_is_checked_and_empty_is_unknown(self, store):
        store.edit("products.csv", COKE, allergens_contains="none")
        assert store.load().products["7123456"].allergens_contains == ()
        store.edit("products.csv", COKE, allergens_contains="")
        assert store.load().products["7123456"].allergens_contains is None
        store.edit("products.csv", COKE, allergens_contains="milk| soya")
        assert store.load().products["7123456"].allergens_contains == ("milk", "soya")

    def test_two_state_columns_load_as_plain_booleans(self, store):
        loaded = store.load()
        assert loaded.stock["7123456"].ranged is True
        assert loaded.products["7123456"].own_brand is False

    def test_identifiers_stay_text(self, store):
        coke = store.load().products["7123456"]
        assert isinstance(coke.sku, str) and isinstance(coke.barcode, str)
        assert len(coke.barcode) == 13
