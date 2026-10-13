"""Catalogue — the products this store could sell (lld.md §7)."""

from functools import cached_property

from config import SEARCH_LIMIT
from models.domain import Product, Store
from services.search import QueryFilter, Scored, SearchIndex


class Catalogue:
    def __init__(self, store: Store):
        self._store = store
        self._products = store.products

    @cached_property
    def index(self) -> SearchIndex:
        return SearchIndex(self._store)

    def search(
        self, term: str, filt: QueryFilter | None = None, limit: int = SEARCH_LIMIT
    ) -> list[Scored]:
        return self.index.search(term, filt, limit)[0]

    def by_sku(self, sku: str) -> Product | None:
        return self._products.get(sku)

    def by_category(self, category: str) -> list[Product]:
        return sorted(
            (p for p in self._products.values() if p.aisle_category == category),
            key=lambda p: p.sku,
        )
