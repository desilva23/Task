# Feature Specification: The LangGraph Pipeline (Phase 5)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-13 ·
**Status**: Draft

**Input**: "Phase 5 — LangGraph: eleven nodes, interrupt, verify, fake model client. Proven by
AC-03, AC-10, AC-11, AC-18."

IDs here are local (`P5-…`). The design is `lld.md` §5, §6, §9 (verify), §11 (the three calls) and
§16 (sequences), amended in this phase as recorded below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask, don't guess, and keep everything else (Priority: P1)

A shopper searches "milk, bread, eggs". Milk and bread are ambiguous, so the journey pauses and
asks; the shopper picks; the journey carries on with eggs still resolved — nothing retyped.

**Acceptance Scenarios**:
1. **Given** an ambiguous term, **Then** the run pauses with a choice of options; **When** the
   shopper chooses, **Then** the choice resolves and the other terms are kept (AC-03, FR-05).
2. **Given** a shopper who never answers well, **Then** clarification stops after two rounds and
   the top-ranked option is used, with a note (EC-35).
3. **Given** a clarification abandoned for longer than the thread lifetime, **Then** its saved
   state is swept (EC-34).

### User Story 2 - Nothing reaches the page unchecked (Priority: P1)

Every run that makes a claim ends at `verify`, which re-derives each fact from the services and
compares. A wrong aisle, distance, floor change or availability is caught, the composed text is
discarded, and the template — built from the same service results — is shown instead.

**Acceptance Scenarios**:
1. **Given** a model description that names the wrong aisle, a wrong distance, stairs for a lift,
   or drops the shelf, **Then** it is blocked, the template is shown, and the mismatch recorded
   (AC-10, NFR-02, EC-47).
2. **Given** a corrupted availability or location statement in state, **Then** it is blocked.
3. **Given** the compiled graph, **Then** `describe_route → verify → END` are plain edges, and no
   path reaches the end after a route without passing `verify`.

### User Story 3 - The model can fail and nothing wrong is said (Priority: P1)

**Acceptance Scenarios**:
1. **Given** every model call failing, **Then** each journey — single product, multi-product,
   step-free, ambiguous, natural language, sold out — returns the same availability and the same
   route as with a working model, and `degraded` names each node that fell back (AC-11, NFR-04,
   EC-37).
2. **Given** a model reply with a field outside its schema (a SKU, a product name), **Then** it is
   rejected and the fallback used (AC-18, FR-04, EC-38).
3. **Given** a natural-language request, **Then** every SKU returned exists in `products.csv`, even
   when the model invents an item name (AC-18).
4. **Given** a substitute the model picks from outside the candidate list, **Then** it is dropped
   and the deterministic list used (`GroundingError`).

### User Story 4 - Two runs: results, then a route (Priority: P1)

A one-product search routes in the same run. A multi-product search returns results only; a
second run plans the route from the basket (`lld.md` §16).

**Acceptance Scenarios**:
1. **Given** "Coca-Cola Classic", **Then** one run returns availability, location, a route and
   verified directions.
2. **Given** a batch, **Then** the run returns results and no route; `plan_route` with the
   basket returns a multi-stop route ending at a till.
3. **Given** a sold-out seasonal product, **Then** its seasonal bay is not offered as a location
   (EC-24); a sold-out product still shows where it usually is (EC-13).

### Edge Cases

- A start node that is not in the graph falls back to the entrance and records the error.
- A category query (EC-09) and an all-unresolved query (EC-03) end without a route.
- A not-ranged product (EC-04) gets in-stock alternatives and no route.

## Requirements *(mandatory)*

- **P5-R01**: Eleven nodes per `lld.md` §6, wired with the §6 routers as amended; `verify` on a
  plain edge after `describe_route`, and the results-only exit through `verify`.
- **P5-R02**: State holds plain values only; `degraded`, `errors` and `mismatches` reset per run.
- **P5-R03**: `ModelClient.complete(task, schema, system, user)` returns raw output; each model
  node validates with the schema (`extra="forbid"`) and falls back on any failure, recording it.
- **P5-R04**: `verify` performs the five §9 checks against freshly derived service facts.
- **P5-R05**: Directions and result statements have deterministic templates that name floor,
  aisle, rack, shelf and every floor change (feeding AC-27 in Phase 7).
- **P5-R06**: Shopper text is passed to a model only as data in the user message, never in the
  instructions (EC-11).
- **P5-R07**: `run_query`, `resume`, `plan_route` per `lld.md` §11, framework-free so the page in
  Phase 7 is a thin caller.

## Success Criteria *(mandatory)*

- **P5-SC1**: AC-03, AC-10, AC-11, AC-18 pass.
- **P5-SC2**: With the model off and with a working fake model, the same journeys yield
  identical availability and routes — the model never changes a fact.
- **P5-SC3**: A one-product journey with the fake model completes in under 200 ms.

## Assumptions

- The four amendments to `lld.md` §6 are recorded there: results-only runs end through `verify`;
  `plan_route` enters at `resolve_locations`; state holds plain values; one model adapter.
- The basket is replaced on each `plan_route`, not merged by a reducer: the page owns the draft.
- One clarification round asks about every ambiguous term at once.
