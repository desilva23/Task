"""Catalogue — the products this store could sell (lld.md §7)."""

from functools import cached_property

from config import SEARCH_LIMIT
from models.domain import Product, Store
from services.search import QueryFilter, Scored, SearchIndex


class Catalogue:
    def __init__(self, store: Store):
        self._store = store
        self._products = store.products
        self._by_barcode = {p.barcode: p for p in store.products.values() if p.barcode}

    @cached_property
    def index(self) -> SearchIndex:
        return SearchIndex(self._store)

    def search(
        self, term: str, filt: QueryFilter | None = None, limit: int = SEARCH_LIMIT
    ) -> list[Scored]:
        return self.index.search(term, filt, limit)[0]

    def by_sku(self, sku: str) -> Product | None:
        return self._products.get(sku)

    def by_barcode(self, code: str) -> Product | None:
        """Exact — V-21 makes every code unique, so a code is one product or none (FR-03)."""
        return self._by_barcode.get(code)

    def by_category(self, category: str) -> list[Product]:
        return sorted(
            (p for p in self._products.values() if p.aisle_category == category),
            key=lambda p: p.sku,
        )


DIET_FIELDS = ("diet_gluten_free", "diet_vegan", "diet_vegetarian", "diet_halal")


def dietary_compatible(candidate: Product, original: Product) -> bool:
    """A substitute must keep every dietary property the original is recorded to have, and add
    no allergen. Unknown never satisfies a requirement (lld.md §9, NFR-03)."""
    for field in DIET_FIELDS:
        if getattr(original, field) is True and getattr(candidate, field) is not True:
            return False
    if original.allergens_contains is not None:
        if candidate.allergens_contains is None:
            return False
        if not set(candidate.allergens_contains) <= set(original.allergens_contains):
            return False
    return True
