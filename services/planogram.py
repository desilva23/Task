"""Planogram — where each SKU sits (lld.md §7). A SKU may sit in several places, or none."""

from collections import defaultdict

from models.domain import Location, Placement, Store

NEEDS_COLLEAGUE = {"COUNTER", "ASSISTED"}  # FR-12, EC-22, EC-23


class Planogram:
    def __init__(self, store: Store):
        self.version = store.info.planogram_version
        self._nodes = store.nodes
        self._by_sku: dict[str, list[Placement]] = defaultdict(list)
        for p in sorted(store.placements, key=lambda p: (p.sku, p.node_id)):
            self._by_sku[p.sku].append(p)

    def for_sku(self, sku: str) -> list[Placement]:
        return list(self._by_sku.get(sku, []))  # may be [] — EC-19

    def for_skus(self, skus: list[str]) -> dict[str, list[Placement]]:
        return {s: self.for_sku(s) for s in skus}

    def locations(self, sku: str) -> list[Location]:
        return [self.location(p) for p in self.for_sku(sku)]

    def location(self, p: Placement) -> Location:
        node = self._nodes[p.node_id]
        return Location(
            node_id=p.node_id,
            level=node.level,
            floor_name=node.floor_name,
            aisle=node.aisle,
            rack=node.rack,
            shelf_no=p.shelf_no,
            location_type=p.location_type,
            needs_colleague=p.location_type in NEEDS_COLLEAGUE,
        )
