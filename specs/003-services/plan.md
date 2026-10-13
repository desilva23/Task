# Implementation Plan: Services and Route Engine (Phase 2)

**Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

Four small services over the loaded `Store`, and a route engine that precomputes all-pairs
shortest paths with scipy for the full and step-free graphs. Built test-first against the demo
store, with AC-04 proven by an independent heap-based Dijkstra in the test itself.

## Technical Context

**Language**: Python 3.12 · **New dependency**: `scipy` (brings `numpy`) — named by the
constitution · **Testing**: pytest, plus `hypothesis` for random start–target pairs ·
**Performance**: matrices for 314 nodes in well under 1 s; `distance` O(1)

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | Every fact comes from the store through these services; no model anywhere | ✅ |
| II | Services pass `bool | None` through untouched; nothing reads a dietary flag for truth yet | ✅ |
| III | Tests first, each citing its AC/FR/EC | ✅ |
| IV | `services/*` imports `scipy`, `numpy`, `models`, `errors` only — the Phase 0 test enforces it | ✅ |
| VI | Services are built only from a `Store`, which exists only if it loaded completely | ✅ |
| VII | All-pairs Dijkstra precomputed once, looked up per request; no A*, no caching layer | ✅ |

## Project Structure

```text
models/domain.py      + Availability, Location, Route, NoRoute
errors.py             + InvalidNodeError, UnreachableNodeError
services/catalogue.py Catalogue — by_sku, by_category
services/stock.py     Stock — positions, availability, AVAILABILITY_TEXT
services/planogram.py Planogram — for_sku, for_skus, locations
services/storegraph.py StoreGraph — open graph, index, CSR per mode, edge per hop, without()
services/routing.py   RouteEngine — matrices, distance, path, hops, route_single, closed()
tests/unit/test_services.py   AC-01, AC-20, AC-21 (locations), FR-12, EC-19
tests/unit/test_routing.py    AC-04, AC-06, AC-07, AC-21, EC-25, EC-29, EC-30, EC-31, EC-32
```

## Complexity Tracking

None.
