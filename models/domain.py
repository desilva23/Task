"""Typed records for one loaded store (schema.md §4).

Three-state values keep unknown apart from false (constitution Principle II): a ``diet_*``
field is ``True``, ``False`` or ``None``, and ``allergens_contains`` is ``None`` (unknown),
``()`` (checked, contains none) or the named allergens.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from errors import Fault


@dataclass(frozen=True)
class StoreInfo:
    store_id: str
    store_name: str
    data_provenance: str
    planogram_version: date
    stock_as_of: datetime


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    brand: str
    size: str
    barcode: str | None
    department: str
    aisle_category: str
    synonyms: tuple[str, ...]
    diet_gluten_free: bool | None
    diet_vegan: bool | None
    diet_vegetarian: bool | None
    diet_halal: bool | None
    allergens_contains: tuple[str, ...] | None
    age_restricted: bool
    price_gbp: float
    own_brand: bool
    popularity: float


@dataclass(frozen=True)
class StockPosition:
    sku: str
    ranged: bool
    shelf_qty: int


@dataclass(frozen=True)
class Placement:
    sku: str
    node_id: str
    location_type: str
    shelf_no: int | None
    facing_from: int | None
    facing_count: int | None
    seasonal: bool


@dataclass(frozen=True)
class MapNode:
    node_id: str
    node_type: str
    level: int
    floor_name: str | None
    aisle: int | None
    rack: int | None
    shelf_count: int | None
    zone: str | None
    x_m: float
    y_m: float
    is_open: bool


@dataclass(frozen=True)
class MapEdge:
    edge_id: str
    from_node: str
    to_node: str
    kind: str
    weight_m: float
    penalty_m: float
    bidirectional: bool
    step_free: bool
    trolley: bool
    is_open: bool


@dataclass(frozen=True)
class Store:
    """A store that passed every refusal. ``warnings`` holds the W-rules it raised."""

    info: StoreInfo
    products: dict[str, Product]
    stock: dict[str, StockPosition]
    placements: tuple[Placement, ...]
    nodes: dict[str, MapNode]
    edges: tuple[MapEdge, ...]
    warnings: tuple[Fault, ...] = field(default=())
