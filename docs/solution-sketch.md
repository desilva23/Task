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

## Algorithms — do we actually need pathfinding?

Mostly no, and this is worth getting right because it's where this kind of
project gets over-engineered. **A supermarket is not a maze.** It is a set of
parallel aisles joined by cross-aisles at the front and back. That regularity
means the classic graph-search answer is usually unnecessary.

Work up the tiers and stop at the first one that meets the requirement.

### Tier 0 — No algorithm at all

> "Aisle 7, bay 3, eye level."

Shoppers can navigate a supermarket. What they don't know is *which aisle*.
Tell them the aisle and the job is done — no graph, no route, no map. This
answers the real question behind "where is it", and it is the fastest thing to
ship. Most of the value in this whole project lives here.

### Tier 1 — Sort by aisle order (serpentine / S-shape)

For a shopping list, sort the items into walking order and snake through the
store: aisle 2 front-to-back, aisle 4 back-to-front, and so on. One sort on an
aisle sequence number. No graph.

This is what most real grocery picking systems actually do, and the warehouse
picking literature consistently puts S-shape traversal within single-digit to
low-double-digit percent of the true optimum. More importantly it produces a
route a human will *follow*. A mathematically optimal route that zig-zags
unpredictably gets abandoned by pickers, and an abandoned route saves nothing.
**Compliance beats optimality.**

### Tier 2 — Precomputed distance matrix

Needed once you want real distances or ETAs ("45 m, about a minute").

Build the store graph, then compute **all-pairs shortest paths once per layout
version**, offline — Floyd–Warshall, or Dijkstra from every node. A superstore
is maybe 30–40 aisles and 200–400 bay nodes; Floyd–Warshall on 400 nodes is
~64M operations, i.e. well under a second, run once and cached.

Every runtime query is then an **O(1) table lookup**. There is no pathfinding
at request time at all. This is the key move: you are not searching, you are
reading a precomputed answer.

### Tier 3 — Route sequencing for a list

Only when the *order* genuinely matters (colleague picking a 60-item order).
Note what the problem actually is: **sequencing, not pathfinding.** The
shortest paths are already in the Tier 2 matrix; what's left is TSP.

- Nearest-neighbour construction, then 2-opt improvement, over the precomputed
  matrix. Milliseconds for 40–80 stops.
- Because a SKU can sit in several locations (home bay *and* promo end cap),
  it's strictly a *generalised* TSP — pick one node per item group.
  Nearest-neighbour handles this naturally by taking the closest member of each
  group.
- Constraints go on top as ordering rules: chilled and frozen last, heavy items
  first, don't put bananas under bleach, respect one-way aisles via directed
  edges.
- For a single-block layout there is an exact polynomial-time algorithm
  (Ratliff–Rosenthal, 1983) if the heuristic ever proves not good enough. It
  almost certainly will be good enough.

### Where Dijkstra/A* genuinely earn their place

Real graph search becomes the right answer when any of these are true:

- **Arbitrary start points.** The moment QR aisle markers let someone start
  mid-store, "route from anywhere to anywhere" is the requirement — though
  Tier 2's precomputed matrix already covers it.
- **Constraint filtering per user.** Step-free routes, closed aisles, cleaning
  in progress, staff-only areas. You filter the graph and re-search; a single
  precomputed matrix can't express every variant, so keep a live search
  available as the fallback path.
- **Irregular or multi-floor layouts.** Hybrid and city-centre stores aren't
  tidy grids, and multi-floor with lifts and escalators needs a real graph.
- **Congestion weighting**, if "optimal" ever means "fastest given where
  everyone else is".

Even then: Dijkstra on a few hundred nodes is microseconds. **A\* buys nothing
at this scale** — the heuristic only pays off on large search spaces, and
adding one is complexity without benefit here. Use plain Dijkstra and move on.

### The trap to avoid

Don't model the floor as a fine-grained occupancy grid and run A* over it. That
is robot navigation, and it will happily route diagonally through a shelf unit
unless you fight it. Humans walk aisles, so **model aisles and bays as nodes**.
The graph should look like the store's own vocabulary — aisle, bay, cross-aisle
— because that's also what the directions have to say out loud.

### And check what "optimal" means

For a shopper, "optimal" almost certainly means *comprehensible*, not minimal.
A route that saves 12 metres but reads strangely will be ignored. Worth
confirming with the stakeholder (Q12) before optimising for the wrong thing.

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
