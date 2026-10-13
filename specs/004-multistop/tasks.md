---
description: "Task list for Phase 3 — multi-stop routing and the basket"
---

# Tasks: Multi-Stop Routing and the Basket (Phase 3)

- [X] T001 Amend `docs/lld.md` §10 (chilled last within the floor pass) — spec first
- [X] T002 Write failing `tests/unit/test_multistop.py`: AC-05, AC-23, AC-24, EC-17, EC-26, EC-33, EC-46, step-free exclusion, multi-placement floor preference, property suite (P3-SC2), 30-item timing
- [X] T003 Add domain types; implement `services/basket.py` and `services/multistop.py` until T002 passes
- [X] T004 Regenerate the matrix; `scripts/check.sh` green; gate record; stop at the gate

## Gate record (2026-10-13)

- `scripts/check.sh` green; Phase 3's 13 tests pass in under a second.
- AC-05, AC-23, AC-24 proven; also EC-17, EC-20, EC-26, EC-27, EC-31, EC-33, EC-46.
- Property suite: 200 random baskets (1–12 items, any start, with and without step-free) — every
  item visited once, floors highest first with one pass each, ends at a till, distance equals
  the sum of hops, step-free routes use no stairs (P3-SC2).
- A 30-item basket routes in under 100 ms (P3-SC3).
- Decisions for the owner: `lld.md` §10 amended — chilled items last within their own floor's
  pass, not after every floor; a second placement never adds a floor; a stop with no step-free
  path is excluded and stated rather than refusing the whole route.
- **Gate approved by the owner, 2026-10-13.**
