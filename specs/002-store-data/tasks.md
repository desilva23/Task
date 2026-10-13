---
description: "Task list for Phase 1 — synthetic store generator and store validator"
---

# Tasks: Synthetic Store Generator and Store Validator (Phase 1)

**Tests**: required (constitution III). Each test task is seen failing before its implementation.

## Phase 1: Setup

- [X] T001 Amend `docs/schema.md` with V-07 and correct `docs/lld.md` §13's rule count; update the Phase 0 ID-total test (spec first, then tests)
- [X] T002 [P] `models/domain.py` frozen dataclasses and `errors.py` `Fault` / `StoreDataError` per contracts/loader-and-generator.md

## Phase 2: User Story 3 — the generator (P1)

- [X] T003 [US3] Write failing `tests/unit/test_generator.py`: determinism (two runs identical), sizes (5 / 180 / 180 / ~250 / 314 / 352, all edges bidirectional), files sorted by PK, UTF-8 no BOM, LF only, committed `data/SBY-DEMO-001` equals a fresh run
- [X] T004 [US3] Implement `datagen/layout.py` (map per `schema.md` §8), `datagen/catalogue.py` (curated aisles, items, anchors), `datagen/build.py` and `datagen/__main__.py`; generate and commit `data/SBY-DEMO-001/`

## Phase 3: User Stories 1 and 2 — the loader (P1)

- [X] T005 [US1] Write failing `tests/conftest.py` fixtures (session-generated store, per-test copy, CSV mutation helpers)
- [X] T006 [P] [US2] Write failing `tests/unit/test_three_state.py` (CONST-II, NFR-03): three distinct diet values, three distinct allergen values, two-state empty refused
- [X] T007 [P] [US1] Write failing `tests/unit/test_refusals_format.py` — V-01…V-07
- [X] T008 [P] [US1] Write failing `tests/unit/test_refusals_files.py` — V-10…V-65
- [X] T009 [P] [US1] Write failing `tests/unit/test_refusals_graph.py` — V-70…V-74, plus stage behaviour (all faults of a stage reported; later stages skipped)
- [X] T010 [P] [US1] Write failing `tests/unit/test_warnings.py` — W-01…W-05, and the demo store's exactly-one-warning
- [X] T011 [US1] Implement `validation.py` stage by stage until T006–T010 pass

## Phase 4: User Story 4 — anchors (P2)

- [X] T012 [US4] Write `tests/unit/test_demo_anchors.py` asserting every anchor in spec.md User Story 4 through `load_store`; adjust the catalogue only if an anchor is missing

## Phase 5: Polish

- [X] T013 Time the demo store load (P1-SC4); regenerate `docs/traceability.md`; `scripts/check.sh` green
- [X] T014 Update `CLAUDE.md` state and the deferred list (the schema now has V-07, which the published schema page and Doc lack); stop at the gate

## Dependencies

T001 → T002 → T003 → T004 → T005 → (T006–T010 in parallel) → T011 → T012 → T013 → T014.

## Gate record (2026-10-13)

- `scripts/check.sh`: 142 passed, ruff clean. Demo store loads in ~10 ms (P1-SC4).
- 43 of 43 refusals and 5 of 5 warnings each proven by a test that breaks only that rule (P1-SC1).
- Demo store: 180 products, 253 placements, 314 nodes, 352 edges; one warning, W-02 for
  Sparkling Water Lime, as intended (P1-SC2). Regenerating from seed 20261013 reproduces the
  committed files byte for byte (P1-SC3).
- Decisions for the owner: V-07 added to the schema; C- and A- IDs made citable (constitution
  1.2.0); module docstrings may carry citations; E501 handed to the formatter; anchor tests cite
  C-04, not the ACs they serve, so the matrix never shows an AC as proven before its phase.
- **Gate approved by the owner, 2026-10-13.**
