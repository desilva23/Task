"""Stock — the branch position (lld.md §7). Availability is read, never inferred."""

from datetime import datetime

from models.domain import Availability, StockPosition, Store

AVAILABILITY_TEXT = {
    Availability.IN_STOCK: "In stock",
    Availability.SOLD_OUT: "Sold out at this store right now",
    Availability.NOT_RANGED: "Not sold at this store",
    Availability.UNKNOWN: "Stock level unknown",
}


class Stock:
    def __init__(self, store: Store):
        self.as_of: datetime = store.info.stock_as_of
        self._positions = store.stock

    def positions(self, skus: list[str]) -> dict[str, StockPosition]:
        """Batched: one call for a whole basket. A SKU with no position is left out."""
        return {s: self._positions[s] for s in skus if s in self._positions}

    def availability(self, sku: str) -> Availability:
        position = self._positions.get(sku)
        if position is None:
            return Availability.UNKNOWN
        if not position.ranged:
            return Availability.NOT_RANGED
        return Availability.IN_STOCK if position.shelf_qty > 0 else Availability.SOLD_OUT
