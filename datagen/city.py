"""SBY-CITY-003 — the city flagship: five floors (FR-25, AC-09, FR-31).

The demo catalogue in a tall, narrow building: one category to an aisle, 36 aisles over five
floors — fresh food at street level, then food cupboard and drinks, snacks, beer and wine (with
the spirits cabinet), health and household, and pets, baby and home at the top (with the baby
cabinet). Six racks to an aisle, six tills, and its own shelf quantities. Nothing in the code
knows it has five floors: the route engine, floor order, step-free matrix and floor plates all
read it from the map.
"""

from datagen.layout import Floor
from datagen.variant import Variant, build_variant_rows

CITY = Variant(
    store_id="SBY-CITY-003",
    name="City Flagship",
    floors=(
        Floor(0, "Fresh Food", 12),
        Floor(1, "Food Cupboard & Drinks", 8),
        Floor(2, "Snacks, Beer & Wine", 6),
        Floor(3, "Health & Household", 6),
        Floor(4, "Pets, Baby & Home", 4),
    ),
    packing={0: [1] * 12, 1: [1] * 8, 2: [1] * 6, 3: [1] * 6, 4: [1] * 4},
    extras=(
        ("F0-ENTRANCE", "entrance", 6.0, 36.0, "Entrance", "F0-A01-S"),
        *(
            (f"F0-TILL-{i:02}", "till", 6.0 * (i + 2), 34.0, "Checkouts", f"F0-A{i + 2:02}-S")
            for i in range(1, 7)
        ),
        ("F0-CTR-01", "counter", 12.0, 2.0, "Deli Counter", "F0-A02-N"),
        ("F0-CTR-02", "counter", 24.0, 2.0, "Fish Counter", "F0-A04-N"),
        ("F0-CTR-03", "counter", 36.0, 2.0, "Bakery Counter", "F0-A06-N"),
        ("F2-CAB-01", "cabinet", 36.0, 2.0, "Spirits", "F2-A06-N"),
        ("F4-CAB-01", "cabinet", 12.0, 2.0, "Baby", "F4-A02-N"),
        ("F0-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F0-A02-S"),
        ("F1-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F1-A02-S"),
    ),
    rear_core_x=78.0,
    racks=6,
    shelves=5,
    spot_nodes={"F1-CAB-01": "F2-CAB-01", "F2-CAB-01": "F4-CAB-01"},
    restock_seed=20261016,
)


def build_city_rows(demo):
    return build_variant_rows(demo, CITY)
