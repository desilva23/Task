# Feature Specification: Multi-Stop Routing and the Basket (Phase 3)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-13 ·
**Status**: Draft

**Input**: "Phase 3 — multi-stop routing: floor order, open-path 2-opt, checkout. Proven by AC-05,
AC-23, AC-24."

IDs here are local (`P3-…`). The algorithm is `lld.md` §10 (multi, nn_then_2opt); the basket gate
is `hld.md` §3.4.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One walk for the whole basket (Priority: P1)

A shopper with items on several floors gets one route: the highest floor first, one picking pass
per floor, working down, finishing at a checkout.

**Independent Test**: a basket spanning all three floors, from the entrance — the stops come
floor 2, then 1, then 0, each floor's stops together, and the route ends at a till.

**Acceptance Scenarios**:
1. **Given** items on all three floors, **Then** the stops are visited floor by floor, highest
   first, each floor once, and the route ends at a till (AC-05, FR-14, FR-16, FR-17, FR-18, EC-27).
2. **Given** all items on one floor and a start on that floor, **Then** the route never changes
   floor until it heads for the tills (EC-26).
3. **Given** chilled items, **Then** they are picked last in their floor's pass (EC-33).
4. **Given** any basket, **Then** the route's distance equals the sum of its hops, and 2-opt never
   makes a floor's sequence longer than nearest-neighbour alone.

### User Story 2 - The basket is what gets routed (Priority: P1)

Items added from separate searches accumulate in one basket, and the route covers every routable
item in it, wherever it came from. An unavailable item may be added on purpose; it stays in the
basket, marked not routable, is left out of the route, and the route says so.

**Acceptance Scenarios**:
1. **Given** items added in three separate additions, **Then** all appear in the basket and the
   route visits every routable one (AC-23, FR-23).
2. **Given** a sold-out item added individually, **Then** it is in the basket marked not routable,
   absent from the route, and its exclusion is stated (AC-24, FR-24, EC-46).
3. **Given** an item that was routable when added and is no longer, **Then** the next route
   re-checks and excludes it — the basket is never trusted from earlier state (EC-17).

### Edge Cases

- A SKU with several placements: prefer one on a floor the basket already visits, then the
  nearest to the start — so a second placement never adds a floor.
- Several SKUs on one rack: one stop each, zero distance between them.
- Step-free: a stop with no step-free path is excluded and the exclusion stated, rather than the
  whole route refused.
- An empty routable set: a `NoRoute` saying nothing in the basket can be routed.

## Requirements *(mandatory)*

- **P3-R01**: `Basket` holds SKUs in the order added, without duplicates, across any number of
  additions; adding returns a new basket.
- **P3-R02**: Routability is assessed on every call from current stock, planogram and graph:
  routable means in stock with at least one open placement. Each non-routable item carries a
  reason and a sentence.
- **P3-R03**: `route_multi` orders floors highest first; within each floor, ambient stops then
  chilled stops, each sequenced by nearest neighbour then open-path 2-opt from the floor's entry
  point; the route ends at the till nearest the last stop.
- **P3-R04**: The 2-opt compares whole open-path lengths, so it has no wrap-around term and stays
  correct on one-way edges.
- **P3-R05**: The result lists stops in order (SKU and placement), the full node path, distance,
  the till, and every excluded item with its sentence.
- **P3-R06**: No model, and `services/*` import rules unchanged.

## Success Criteria *(mandatory)*

- **P3-SC1**: AC-05, AC-23, AC-24 pass.
- **P3-SC2**: Over 200 random baskets (hypothesis), every invariant holds: all routable items
  visited exactly once, floors non-increasing across stops, ends at a till, distance equals the
  sum of hops, 2-opt ≤ nearest-neighbour.
- **P3-SC3**: A 30-item basket routes in under 100 ms.

## Assumptions

- **Chilled last within the floor, not after all floors.** `lld.md` §10's pseudocode appends every
  chilled stop after the floor passes, which would send a shopper back upstairs if a chiller sat
  above the ground floor and break FR-17. Putting chilled stops last within their own pass keeps
  FR-17 and still makes them last overall in the demo store, where every chiller is on floor 0.
  `lld.md` §10 is amended to match.
- Consecutive stops are joined by their direct shortest path; the floor's entry core seeds the
  nearest-neighbour order. A shortest path between floors passes a core anyway.
- One routable item still gets a route ending at a till here; sending it down the single-product
  path instead (EC-28) is the graph's routing decision, in Phase 5.
- The "add all available" action (FR-22, AC-08) is the page's, in Phase 7.
