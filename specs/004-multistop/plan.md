# Implementation Plan: Multi-Stop Routing and the Basket (Phase 3)

**Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

A basket value type, a routability check run fresh on each call, and `route_multi` per `lld.md`
§10 with one amendment (chilled last within the floor). Tests first, including a hypothesis
property suite over random baskets.

## Technical Context

Python 3.12 · no new dependency · pytest + hypothesis · ≤ 30 stops, so the 2-opt's whole-path
recompute (O(n³) lookups) is ~27k matrix reads at worst.

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | Stops, order, distance and till come from the services and matrices only | ✅ |
| III | Tests first; AC-05/23/24, EC-17/26/27/33/46 cited | ✅ |
| IV | `services/basket.py`, `services/multistop.py` import services, models, errors only | ✅ |
| VII | Nearest neighbour + open 2-opt; no solver library | ✅ |

## Project Structure

```text
models/domain.py        + BasketItem, Stop, Excluded, MultiRoute
services/basket.py      Basket, assess()
services/multistop.py   route_multi, nn_then_2opt
tests/unit/test_multistop.py
docs/lld.md §10         amended: chilled last within the floor pass
```

## Complexity Tracking

None.
