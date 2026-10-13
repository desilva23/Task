# Implementation Plan: Synthetic Store Generator and Store Validator (Phase 1)

**Branch**: `claude/planogram-store-navigation-czn7bh` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

A pure-Python loader that turns a store folder into typed records or refuses it with every
fault named, and a seeded generator that writes the three-floor demo store. Both are built
test-first: one test per V-rule breaks a valid generated store in exactly one place.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: none new — standard library `csv`, `dataclasses`, `random`
**Storage**: six CSV files per store folder under `data/`
**Testing**: pytest; a session-scoped generated store copied per test and mutated
**Target Platform**: as Phase 0
**Project Type**: single application
**Performance Goals**: demo store loads and validates in under 1 s (P1-SC4)
**Constraints**: loader must import nothing from `graph/`, `ui/`, LangChain, LangGraph, Streamlit
**Scale/Scope**: 180 products, ~250 placements, 314 nodes, 352 edges

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | No model involvement; data is the only source of facts | ✅ |
| II | `diet_*` → `bool | None`; allergens → `tuple[str, ...] | None` with `()` for `none`; empty never coerced; tested | ✅ |
| III | 43 V-tests + 5 W-tests written before the loader; each cites its V/W ID and AC-14 | ✅ |
| IV | `validation.py`, `models/`, `datagen/` import only the standard library; the Phase 0 import test covers them | ✅ |
| V | n/a | ✅ |
| VI | `load_store` returns a `Store` only if every refusal passes; otherwise raises `StoreDataError` | ✅ |
| VII | BFS over a dict for connectivity; no pandas, no scipy in this phase | ✅ |

## Project Structure

```text
specs/002-store-data/   spec.md · plan.md · research.md · contracts/ · quickstart.md · tasks.md
models/domain.py        StoreInfo, Product, StockPosition, Placement, MapNode, MapEdge, Store
errors.py               Fault, StoreDataError
validation.py           load_store(folder) -> Store; stages parse → within-file → referential → graph; warnings
datagen/
  __init__.py
  __main__.py           python -m datagen [--seed N] [--out DIR]
  layout.py             floors, aisles, cores, tills, counters → nodes and edges
  catalogue.py          the curated aisles, items and anchors
  build.py              assemble rows with the seed; write sorted CSVs
data/SBY-DEMO-001/      the six generated files (committed)
tests/
  conftest.py           demo_store (session) and store_copy fixtures; CSV mutation helpers
  unit/test_three_state.py
  unit/test_refusals_format.py      V-01…V-07
  unit/test_refusals_files.py       V-10…V-65
  unit/test_refusals_graph.py       V-70…V-74
  unit/test_warnings.py             W-01…W-05
  unit/test_generator.py            determinism, sizes, committed copy, anchors
```

**Structure Decision**: the `lld.md` §1 layout plus `datagen/` for the generator.

## Complexity Tracking

None.
