# Solution Sketch (pre-clarification, assumptions stated)

This is a straw man to react to, not a design. It exists so the conversation
with the stakeholder has something concrete to push against. Every assumption
is flagged — replace it with their answer.

## Assumptions made

| # | Assumption | Replace with answer to |
|---|---|---|
| A1 | Customer-facing, single product first; shopping list later | Q1, Q6 |
| A2 | Planogram data arrives as a nightly per-store extract | Q2 |
| A3 | Store layout must be modelled by us as a graph | Q3 |
| A4 | Start position = entrance, QR aisle markers in phase 2 | Q4 |
| A5 | Stock is a near-real-time per-store feed, banded for display | Q5 |

## Core data model

Four entities do most of the work:

```
Product        sku, name, brand, size, barcode, category, search_terms[]
StoreLocation  store_id, sku, aisle, bay, shelf, facing, location_type
                 location_type ∈ {HOME, PROMO_ENDCAP, SEASONAL, DUMP_BIN, CHILLER}
                 (one SKU → many locations; see Q8)
StockPosition  store_id, sku, shelf_qty, total_qty, as_of, band
Store layout   nodes + edges (below)
```

`StoreLocation` is the planogram projection. Keeping it separate from `Product`
means a planogram re-set is a bulk replace of one table per store, which is
exactly what a nightly extract wants to do.

## Store layout as a graph

Model the walkable floor as an undirected weighted graph (directed where there
are one-way aisles):

```json
{
  "store_id": "SBY-0421",
  "nodes": [
    { "id": "ENTRANCE",  "type": "entrance", "x": 0,  "y": 0 },
    { "id": "A7_FRONT",  "type": "aisle_end", "x": 42, "y": 8, "aisle": 7 },
    { "id": "A7_B3",     "type": "bay",       "x": 42, "y": 18, "aisle": 7, "bay": 3 },
    { "id": "A7_REAR",   "type": "aisle_end", "x": 42, "y": 30, "aisle": 7 },
    { "id": "CHECKOUT",  "type": "checkout",  "x": 6,  "y": 2 }
  ],
  "edges": [
    { "from": "ENTRANCE", "to": "A7_FRONT", "weight": 42, "via": "main_aisle" },
    { "from": "A7_FRONT", "to": "A7_B3",    "weight": 10 },
    { "from": "A7_B3",    "to": "A7_REAR",  "weight": 12 }
  ]
}
```

Notes:
- **Bays are nodes, not just aisles.** If bays are nodes you can route to
  "aisle 7, bay 3" and the walk distance is honest. Aisle-level nodes make
  every route look the same length.
- Edge weight is metres; swap to seconds if "optimal" turns out to mean time
  (Q12). Congestion can be modelled as a multiplier on edge weight later.
- Accessibility: tag edges `step_free: false` and filter the graph per user
  preference rather than maintaining a second map.

## Algorithms

- **Single product:** A* with Euclidean distance as the heuristic. On a store
  graph of a few hundred nodes this is sub-millisecond; Dijkstra is fine too.
- **Shopping list:** this is TSP over the graph. Practical approach:
  1. Precompute the all-pairs shortest-path matrix per store (a few hundred
     nodes → a small matrix, computed once per layout version, cached).
  2. Nearest-neighbour construction, then 2-opt improvement. Good enough for
     40–80 stops and runs in milliseconds.
  3. Apply constraints as ordering rules on top: chilled/frozen last, heavy
     items first, respect one-way aisles via directed edges.
- **Do not** recompute graphs per request. Precompute per layout version, cache,
  invalidate on planogram/layout change.

## Service shape

```
  Search API  ──► Product Search  (index: name, brand, synonyms, barcode)
                        │
  Locate API  ──────────┼──► Location Service   (planogram projection)
                        ├──► Availability Svc   (stock feed, banded)
                        └──► Routing Service    (graph + A*/TSP, cached)
```

One orchestrating endpoint for the UI, because the screen needs all three at
once:

```
GET /v1/stores/{storeId}/products/search?q=coke+500ml&from=ENTRANCE

{
  "results": [{
    "sku": "7123456",
    "name": "Coca-Cola Classic 500ml",
    "availability": { "band": "IN_STOCK", "as_of": "2026-10-08T09:14:00Z" },
    "locations": [
      { "type": "HOME",         "aisle": 7, "bay": 3, "shelf": 2 },
      { "type": "PROMO_ENDCAP", "aisle": null, "label": "Front end cap A2" }
    ],
    "route": {
      "to": "A7_B3",
      "distance_m": 45,
      "eta_s": 58,
      "steps": ["Head down the main aisle", "Turn into aisle 7", "Bay 3, eye level"]
    }
  }]
}
```

## Suggested phasing

1. **Phase 0 — data feasibility spike.** Get one real store's planogram extract
   and one real floor plan. Everything else is guesswork until this exists.
   This is the phase to argue for first.
2. **Phase 1 — locate only.** Search → availability → "Aisle 7". No map, no
   route. This alone answers most "where is X" questions and ships fast.
3. **Phase 2 — routing from entrance.** Graph model + A*, text directions.
4. **Phase 3 — positioning.** QR aisle markers to set start position.
5. **Phase 4 — shopping list sequencing.** TSP + constraints.
6. **Phase 5 — map visualisation / turn-by-turn,** if the metric justifies it.

The temptation will be to demo phase 6 first. Resist it: the demo is easy and
the data underneath it is what actually decides whether this works.

## Biggest risks to name upfront

1. **Planogram ≠ reality.** Shelves drift from plan within days. Without a
   compliance signal or a user feedback loop, accuracy decays and trust goes
   with it.
2. **Store layout digitisation** is the hidden cost. Per-store manual work
   across a large estate can dwarf the software build.
3. **Stock accuracy** for shelf-level availability is genuinely hard; most
   retailers know total store stock far better than shelf stock.
4. **Indoor positioning** is the classic scope trap — easy to promise, expensive
   to deliver, and avoidable in early phases.
