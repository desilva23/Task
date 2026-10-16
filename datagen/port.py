"""SBY-PORT-002 — the portability store (AC-09, schema.md §8).

Same catalogue and stock as the demo store — the generator's own demo rows, unchanged — on a
differently shaped map: two floors, 15 aisles (8 + 7) of five racks, several categories sharing
an aisle so a rack holds several products on different shelves, four tills, and both locked
cabinets on floor 1. Only the map and the planogram move.
"""

from datagen.layout import Floor
from datagen.variant import Variant, build_variant_rows

PORT = Variant(
    store_id="SBY-PORT-002",
    name="Portability Test Store",
    floors=(Floor(0, "Ground Floor", 8), Floor(1, "First Floor", 7)),
    packing={
        0: [3, 3, 2, 2, 2, 2, 2, 2],  # 18 catalogue aisles on the ground floor
        1: [3, 3, 2, 2, 3, 2, 3],  # 18 on the first
    },
    extras=(
        ("F0-ENTRANCE", "entrance", 6.0, 36.0, "Entrance", "F0-A01-S"),
        *(
            (f"F0-TILL-{i:02}", "till", 6.0 * (i + 2), 34.0, "Checkouts", f"F0-A{i + 2:02}-S")
            for i in range(1, 5)
        ),
        ("F0-CTR-01", "counter", 12.0, 2.0, "Deli Counter", "F0-A02-N"),
        ("F0-CTR-02", "counter", 24.0, 2.0, "Fish Counter", "F0-A04-N"),
        ("F0-CTR-03", "counter", 36.0, 2.0, "Bakery Counter", "F0-A06-N"),
        ("F1-CAB-01", "cabinet", 30.0, 2.0, "Spirits", "F1-A05-N"),
        ("F1-CAB-02", "cabinet", 42.0, 2.0, "Baby", "F1-A07-N"),
        ("F0-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F0-A02-S"),
        ("F1-BIN-01", "bin", 12.0, 31.0, "Front of Store", "F1-A02-S"),
    ),
    rear_core_x=54.0,
    spot_nodes={"F2-CAB-01": "F1-CAB-02"},  # the demo's second-floor cabinet moves down
)


def build_port_rows(demo):
    return build_variant_rows(demo, PORT)
