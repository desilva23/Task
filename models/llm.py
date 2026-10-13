"""Structured outputs (lld.md §9). Note what is absent: no field where a model could put a
product name, a SKU it invented, a location or a distance. ``extra="forbid"`` makes any such
field a validation error rather than a quietly ignored key."""

from pydantic import BaseModel, ConfigDict, Field

from config import MAX_BATCH_TERMS


class ParsedQuery(BaseModel):
    """What the model may say about a request: what kinds of thing, and dietary needs."""

    model_config = ConfigDict(extra="forbid")
    items: list[str] = Field(default_factory=list, max_length=MAX_BATCH_TERMS)
    department: list[str] = Field(default_factory=list)
    aisle_category: list[str] = Field(default_factory=list)
    dietary_required: list[str] = Field(default_factory=list)
    exclude_allergens: list[str] = Field(default_factory=list)


class SubstituteChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: str  # checked against the candidate set the service built
    reason: str = Field(max_length=140)


class RouteDescription(BaseModel):
    """The facts, reworded — one line per fact line, every number kept."""

    model_config = ConfigDict(extra="forbid")
    lines: list[str]
