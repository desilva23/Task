"""resolve_locations — where each product is, what is routable, and the result statements.

A route-planning run enters here, so routability is re-checked from current stock every time
(EC-17). A search for one product puts it in the basket so it routes in the same run (§16.1);
a batch returns results only, and the basket is the shopper's to fill (FR-22).
"""

from graph.nodes.common import subjects
from graph.templates import compose_results, locations_for
from services.basket import Basket, assess


def make_resolve_locations(services, model):
    def resolve_locations(s):
        plan = s.get("action") == "plan"
        skus = subjects(s)
        availability = dict(s.get("availability") or {})
        for sku in skus:
            availability[sku] = services.stock.availability(sku).value
        if plan:
            basket_skus = skus
        elif (
            s.get("shape") in ("term", "barcode")
            and len(skus) == 1
            and availability[skus[0]] == "in_stock"
        ):
            basket_skus = skus
        else:
            basket_skus = []
        items = assess(
            Basket(tuple(basket_skus)),
            services.catalogue,
            services.stock,
            services.planogram,
            services.engine.graph,
        )
        return {
            "availability": availability,
            "locations": {sku: locations_for(services, sku) for sku in skus},
            "basket": [
                {"sku": i.sku, "routable": i.routable, "reason": i.reason, "message": i.message}
                for i in items
            ],
            "results": compose_results(services, s, skus),
        }

    return resolve_locations
