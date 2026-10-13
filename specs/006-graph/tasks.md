---
description: "Task list for Phase 5 — the LangGraph pipeline"
---

# Tasks: The LangGraph Pipeline (Phase 5)

- [X] T001 Amend `docs/lld.md` §6 (verify on every claiming run, plan entry, plain state, model adapter) — spec first
- [X] T002 Add `langgraph`, `pydantic`; probe interrupt/resume and the checkpointer exports
- [X] T003 Write failing `tests/integration/test_graph.py` and `tests/integration/test_verify.py`
- [X] T004 Implement models/llm.py, errors, graph/model.py, services, state, templates, routers
- [X] T005 Implement the eleven nodes, build_graph, journey entry points, thread sweeper — until T003 passes
- [X] T006 Timing (P5-SC3); regenerate the matrix; `scripts/check.sh` green; gate record

## Gate record (2026-10-13)

- `scripts/check.sh`: 248 passed. AC-03, AC-10, AC-11, AC-18 proven; also EC-04, EC-11, EC-13,
  EC-24, EC-34, EC-35, EC-37, EC-38, FR-09, FR-15, FR-23, NFR-02, NFR-04.
- Structure: eleven nodes; `describe_route → verify → END` plain edges; every claiming run ends
  at `verify`.
- AC-10: a wrong aisle, a wrong distance, a dropped shelf, stairs-for-lift in the model's words,
  and a corrupted statement, distance or stop in state — each blocked, template shown, recorded.
- AC-11: five journeys with the model off give the same availability and routes as with it on.
- Timing: startup 35 ms; a one-product journey 3 ms (P5-SC3).
- Decisions for the owner:
  1. Every run that makes a claim ends at `verify`, results-only searches included.
  2. The model adapter returns raw output; our code validates it (`extra="forbid"`).
  3. State holds plain values only; the basket is replaced on each `plan_route`.
  4. **A search fix found here:** which product the shopper *named* is decided by text match
     alone. Ranking by precedence had made "Diet Coke" (sold out) silently answer with Coca-Cola
     Zero, hiding EC-13, and "Pepsi Max" become a Coke (EC-04). `lld.md` §8.4 amended; AC-19's
     ordering of options and alternatives is unchanged.
  5. One clarification round asks about every ambiguous term at once.
