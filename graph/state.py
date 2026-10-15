"""JourneyState (lld.md §5). Plain values only — SKUs, node IDs, numbers and text — so a
checkpoint is safe to serialise and can never carry a stale fact; nodes read facts afresh."""

from typing import Literal, TypedDict


class JourneyState(TypedDict, total=False):
    # request
    action: Literal["search", "scan", "plan"]
    raw_query: str
    barcode: str  # scan only — digits as decoded or typed (FR-03)
    mode: Literal["auto", "single", "multi"]
    start_node: str
    step_free: bool

    # classification
    shape: str
    terms: list[dict]  # {text, qty}
    parsed: dict | None  # ParsedQuery, validated
    sentence: bool  # searched by keywords — never auto-resolved
    message: str | None
    split: list[dict]  # {from, into} — a list said without commas, cut into items (FR-02)

    # resolution, per term index
    term_status: list[str]  # resolved · ambiguous · category · unresolved · not_catalogued
    candidates: list[list[str]]  # ranked SKUs
    category: list[str | None]
    suggestions: list[list[str]]
    resolved: dict[str, str]  # term index → chosen SKU
    unresolved: list[str]
    not_ranged: list[str]
    notes: list[str]

    # facts
    availability: dict[str, str]  # SKU → Availability value
    substitutes: dict[str, list[str]]
    locations: dict[str, list[dict]]  # SKU → [{node_id, location_type, shelf_no}]
    results: list[str]  # the result statements shown to the shopper

    # basket and route
    basket: list[dict]  # {sku, routable, reason, message}
    route: dict | None
    directions: list[str]

    # control
    clarify_rounds: int
    degraded: list[str]
    errors: list[str]
    verified: bool
    mismatches: list[dict]
