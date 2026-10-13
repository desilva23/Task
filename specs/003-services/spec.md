# Feature Specification: Services and Route Engine (Phase 2)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-13 ·
**Status**: Draft

**Input**: "Phase 2 — services: catalogue, stock, planogram, store graph, route engine. Proven by
AC-01, AC-04, AC-06, AC-07, AC-20, AC-21."

IDs here are local (`P2-…`). Interfaces and algorithms are `lld.md` §4, §7 and §10 (single);
this spec does not restate them. Search (Phase 4) and multi-stop routing (Phase 3) are out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Where is it, and is it there? (Priority: P1)

Given a SKU, the services answer whether it is available and exactly where it is — floor,
aisle, rack and shelf — or that it is at a counter or in a locked cabinet with no shelf.

**Independent Test**: Coca-Cola Classic returns "in stock" and F1 · aisle 7 · rack 3 · shelf 2,
plus its end cap; a counter product returns its counter with no shelf and needs a colleague.

**Acceptance Scenarios**:
1. **Given** a ranged, stocked SKU, **Then** availability is *in stock* and every placement comes
   back as a location naming floor, aisle, rack and shelf (AC-01, FR-07, FR-10).
2. **Given** `ranged=false` and, separately, `ranged=true, shelf_qty=0`, **Then** the two states
   differ and so does the sentence for each (AC-20, FR-08).
3. **Given** a counter or cabinet placement, **Then** the location has no shelf and is marked as
   needing a colleague (FR-12, EC-22, EC-23).
4. **Given** a SKU with no placement, **Then** the location list is empty, not invented (EC-19).

### User Story 2 - The shortest walk from where I am (Priority: P1)

From a chosen start point, the route to a product is the shortest walking route in the store map,
to the nearest of its placements.

**Independent Test**: for many start–target pairs, the engine's distance equals a shortest path
computed independently from `map_edges.csv`, and the returned path's hops add up to it.

**Acceptance Scenarios**:
1. **Given** any two open points, **Then** the route distance equals an independently computed
   shortest distance (AC-04, FR-13).
2. **Given** the same product from two start points, **Then** two different routes come back,
   each the shortest from its own start (AC-06, FR-15).
3. **Given** a SKU with two placements and a start nearer the second, **Then** the route targets
   the second, and both locations are still reported (AC-21, FR-11, EC-20).
4. **Given** a start already at the product's rack, **Then** the route is that one point,
   distance 0 (EC-25).

### User Story 3 - Step-free, or an honest no (Priority: P1)

A step-free request crosses floors only by lift and uses no stairs. If closures leave no
step-free path, the answer says so instead of returning stairs.

**Independent Test**: a step-free route from the ground floor to F2 uses lifts at every level
change and no stairs; with both upper lifts closed at run time, the step-free request returns
"no step-free route" while the ordinary request still succeeds by stairs.

**Acceptance Scenarios**:
1. **Given** step-free, **Then** every hop uses a step-free edge and every floor change is a
   lift (AC-07, FR-19).
2. **Given** step-free and no step-free path, **Then** a no-route answer naming the reason comes
   back, never a route with stairs (AC-07, EC-31).
3. **Given** an edge closed at run time, **Then** distances are recomputed without it, and the
   other core carries the route (EC-30).

### Edge Cases

- Parallel lift and stairs between the same cores: the step-free graph filters to step-free
  edges *before* taking the minimum, or the stairs hide the lift (`schema.md` §4.6).
- A start point not in the graph raises `InvalidNodeError` (a bug: the picker is built from the
  graph). A missing path raises `UnreachableNodeError` (a data bug after V-70).
- Placements on closed nodes are not routable (EC-32); if none remain, a no-route answer says
  the location is closed.

## Requirements *(mandatory)*

- **P2-R01**: `Catalogue`, `Stock`, `Planogram` per `lld.md` §7 (search arrives in Phase 4);
  multi-item lookups are list-in, map-out.
- **P2-R02**: Availability is one of *in stock*, *sold out*, *not sold here*, *unknown*, each
  with a distinct fixed sentence; no model is involved.
- **P2-R03**: A location carries node, floor (level and name), aisle, rack, shelf, location type,
  and whether a colleague is needed; shelf is empty for counters, cabinets, end caps and bins.
- **P2-R04**: `StoreGraph` is built from the open nodes and open edges only; effective weight is
  `weight_m + penalty_m`; parallel arcs collapse to the minimum, after the step-free filter for
  the step-free graph.
- **P2-R05**: `RouteEngine` precomputes all-pairs distances and predecessors with
  `scipy.sparse.csgraph.shortest_path(method="D", directed=True)` for the full and step-free
  graphs; `distance` is a lookup, `path` walks predecessors (`lld.md` §4).
- **P2-R06**: `route_single` targets the nearest routable placement and returns a `Route` (node
  path, distance, floors touched, target placement) or a `NoRoute` naming the reason.
- **P2-R07**: The engine can report which edge each hop uses, so directions (Phase 5) can say
  *lift* or *stairs*.
- **P2-R08**: Closing edges at run time rebuilds the matrices without them (EC-30).
- **P2-R09**: `services/*` imports no graph runtime, model client or page framework.

## Success Criteria *(mandatory)*

- **P2-SC1**: Every distance the engine returns between open points equals the independent
  shortest-path computation, over all pairs from a sample of 50 starts (to 1e-9 m).
- **P2-SC2**: Building both matrices for the demo store takes under one second.
- **P2-SC3**: AC-01, AC-04, AC-06, AC-07, AC-20, AC-21 each have a passing test.

## Assumptions

- Availability sentences: *In stock* · *Sold out at this store right now* · *Not sold at this
  store* · *Stock level unknown*. Page styling comes in Phase 7.
- The start point is a node ID; turning the floor-and-aisle picker into one belongs to the page
  (Phase 7). The entrance is the default.
- EC-24 (seasonal suppression) needs stock-aware placement filtering in the graph nodes and is
  left to Phase 5; no Phase 2 AC depends on it.
