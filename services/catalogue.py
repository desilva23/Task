"""Catalogue — the products this store could sell (lld.md §7). Search arrives in Phase 4."""

from models.domain import Product, Store


class Catalogue:
    def __init__(self, store: Store):
        self._products = store.products

    def by_sku(self, sku: str) -> Product | None:
        return self._products.get(sku)

    def by_category(self, category: str) -> list[Product]:
        return sorted(
            (p for p in self._products.values() if p.aisle_category == category),
            key=lambda p: p.sku,
        )
