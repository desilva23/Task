---
description: "Task list for Phase 2 — services and route engine"
---

# Tasks: Services and Route Engine (Phase 2)

**Tests**: required; each test task is seen failing before its implementation.

- [X] T001 Add `scipy` with `uv add`; lock
- [X] T002 [P] Write failing `tests/unit/test_services.py`: availability states and sentences (AC-20), Coca-Cola's locations (AC-01, AC-21), counter and cabinet locations (FR-12), unplaced SKU (EC-19), batched lookups
- [X] T003 [P] Write failing `tests/unit/test_routing.py`: independent Dijkstra equality (AC-04), two starts (AC-06), nearest placement (AC-21), step-free lifts only (AC-07), no step-free route after closures (AC-07, EC-31), runtime closure (EC-30), same-node route (EC-25), closed node not routable (EC-32), invalid start (InvalidNodeError), parallel-edge step-free trap
- [X] T004 Add domain types and errors; implement `services/catalogue.py`, `stock.py`, `planogram.py` until T002 passes
- [X] T005 Implement `services/storegraph.py` and `services/routing.py` until T003 passes
- [X] T006 Time the matrix build (P2-SC2); regenerate the matrix; `scripts/check.sh` green
- [X] T007 Update `CLAUDE.md`; gate record; stop at the gate

## Gate record (2026-10-13)

- `scripts/check.sh`: 165 passed, ruff clean. Both matrices for the demo store build in ~11 ms
  (P2-SC2).
- AC-04: every distance from 50 sampled starts to all 314 points, full and step-free, equals a
  Dijkstra written independently in the test from the raw edge rows (P2-SC1).
- AC-01, AC-06, AC-07, AC-20, AC-21 each proven; also EC-18, EC-19, EC-20, EC-22, EC-23, EC-25,
  EC-29, EC-30, EC-31, EC-32 (P2-SC3).
- Decisions for the owner: availability sentences fixed as *In stock* · *Sold out at this store
  right now* · *Not sold at this store* · *Stock level unknown*; a missing route is a `NoRoute`
  with a plain reason, never a worse route; EC-24 (seasonal suppression) moves to Phase 5.
- **Gate approved by the owner, 2026-10-13.**
