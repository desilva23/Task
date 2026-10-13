"""The basket — what gets routed (FR-23, hld.md §3.4).

The basket holds SKUs only. Whether each one can be routed is worked out afresh on every call
from current stock, planogram and graph, so a stale session can never route to an empty shelf
(EC-17).
"""

from dataclasses import dataclass

from models.domain import Availability, BasketItem
from services.catalogue import Catalogue
from services.planogram import Planogram
from services.stock import Stock
from services.storegraph import StoreGraph

WHY_NOT = {
    "sold_out": "{name} is sold out, so it is left out of the route.",
    "not_ranged": "{name} is not sold at this store, so it is left out of the route.",
    "unknown": "{name}'s stock level is unknown, so it is left out of the route.",
    "no_location": "{name} has no recorded location, so it is left out of the route.",
    "location_closed": "Where {name} is kept is closed right now, so it is left out of the route.",
}
REASON_FOR = {
    Availability.SOLD_OUT: "sold_out",
    Availability.NOT_RANGED: "not_ranged",
    Availability.UNKNOWN: "unknown",
}


@dataclass(frozen=True)
class Basket:
    skus: tuple[str, ...] = ()

    def add(self, *skus: str) -> "Basket":
        """Items from any number of searches accumulate; a repeat is not doubled."""
        return Basket(tuple(dict.fromkeys(self.skus + skus)))


def assess(
    basket: Basket,
    catalogue: Catalogue,
    stock: Stock,
    planogram: Planogram,
    graph: StoreGraph,
) -> list[BasketItem]:
    items = []
    for sku in basket.skus:
        product = catalogue.by_sku(sku)
        name = product.name if product else sku
        availability = stock.availability(sku)
        placements = planogram.for_sku(sku)
        if availability is not Availability.IN_STOCK:
            reason = REASON_FOR[availability]
        elif not placements:
            reason = "no_location"
        elif not any(p.node_id in graph.index for p in placements):
            reason = "location_closed"
        else:
            items.append(BasketItem(sku, name, availability, routable=True))
            continue
        message = WHY_NOT[reason].format(name=name)
        items.append(BasketItem(sku, name, availability, False, reason, message))
    return items
