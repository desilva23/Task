"""Everything the nodes read facts from, built once per store."""

from dataclasses import dataclass

from models.domain import Store
from services.catalogue import Catalogue
from services.planogram import Planogram
from services.routing import RouteEngine
from services.search import SearchIndex
from services.stock import Stock
from services.storegraph import StoreGraph


@dataclass(frozen=True)
class Services:
    store: Store
    catalogue: Catalogue
    stock: Stock
    planogram: Planogram
    engine: RouteEngine
    index: SearchIndex

    @classmethod
    def from_store(cls, store: Store) -> "Services":
        return cls(
            store=store,
            catalogue=Catalogue(store),
            stock=Stock(store),
            planogram=Planogram(store),
            engine=RouteEngine(StoreGraph(store)),
            index=SearchIndex(store),
        )
