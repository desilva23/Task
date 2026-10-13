"""Structured outputs (lld.md §9). Note what is absent: no field where a model could put a
product name, a SKU it invented, a location or a distance. ``extra="forbid"`` makes any such
field a validation error rather than a quietly ignored key."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from config import MAX_BATCH_TERMS

DietaryKey = Literal["gluten_free", "vegan", "vegetarian", "halal"]


class ParsedQuery(BaseModel):
    """What the model may say about a request: what kinds of thing, and dietary needs."""

    model_config = ConfigDict(extra="forbid")
    items: list[str] = Field(default_factory=list, max_length=MAX_BATCH_TERMS)
    department: list[str] = Field(default_factory=list)
    aisle_category: list[str] = Field(default_factory=list)
    dietary_required: list[DietaryKey] = Field(default_factory=list)
    exclude_allergens: list[str] = Field(default_factory=list)


def parsed_query_for(store) -> type[ParsedQuery]:
    """ParsedQuery narrowed to this store's own names. Sent as the strict schema, the model
    cannot produce a category, department or allergen the store does not have — found live,
    when gpt-oss answered "pharmacy" and "over the counter" — and validation rejects one anyway.
    A different store's data narrows it differently, with no code change (FR-25)."""
    products = store.products.values()

    def one_of(values):
        values = tuple(sorted(values))
        return list[Literal[values]] if values else list[str]  # type: ignore[valid-type]

    allergens = {a for p in products for a in (p.allergens_contains or ())}
    # A shopper's words do not say whether "Medicines" is a department or a category, and the
    # model mixed them up live; both fields take any real name and the node files them.
    names = {p.department for p in products} | {p.aisle_category for p in products}
    return create_model(
        "ParsedQuery",
        __base__=ParsedQuery,
        department=(one_of(names), Field(default_factory=list)),
        aisle_category=(one_of(names), Field(default_factory=list)),
        exclude_allergens=(one_of(allergens), Field(default_factory=list)),
    )


class SubstituteChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: str  # checked against the candidate set the service built
    reason: str = Field(max_length=140)


class RouteDescription(BaseModel):
    """The facts, reworded — one line per fact line, every number kept."""

    model_config = ConfigDict(extra="forbid")
    lines: list[str]
