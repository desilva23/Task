# Feature Specification: The Streamlit Page (Phase 7)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-14 ·
**Status**: Draft

**Input**: "Phase 7 — the Streamlit page. Proven by AC-08, AC-15, AC-22, AC-27."

IDs here are local (`P7-…`). The design is `hld.md` §4 and `lld.md` §11.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search, choose, basket, route (Priority: P1)

A shopper on their phone picks where they are (floor, then aisle; the entrance by default), types
one or several products, answers a "which one?" if asked, sees the results grouped with the
available ones first, adds the available ones in one tap, and plans a route.

**Acceptance Scenarios**:
1. **Given** a search where three items are available and one is not, **Then** the results are
   grouped, available first, and one action adds exactly the three to the basket (AC-08, FR-21,
   FR-22).
2. **Given** an unavailable item, **Then** it can still be added on its own, marked not routable
   (FR-24); the route says it was left out.
3. **Given** an ambiguous term, **Then** the page asks with one choice per term and carries on
   from the answer on the next run (FR-05).
4. **Given** the page, **Then** it states the data is synthetic (C-04), and says when the language
   model was unavailable (`degraded`).

### User Story 2 - The route, twice, and the same (Priority: P1)

**Acceptance Scenarios**:
1. **Given** any route, **Then** it is shown as an ordered directions list and drawn on one floor
   plate per floor it touches, and both describe the same sequence of points and stops (AC-22,
   FR-20).
2. **Given** the directions alone, read as plain text with the map removed, **Then** they name
   every stop's floor, aisle, rack and shelf and every floor change; a step-free request uses
   lifts only (AC-27, NFR-10, AC-07).

### User Story 3 - A phone in one hand (Priority: P1)

**Acceptance Scenarios**:
1. **Given** a 390 px wide viewport, **Then** the whole journey completes with no horizontal page
   scroll, and the floor plate fits the width with route markers large enough to read without
   zooming (AC-15, NFR-11).

### Edge Cases

- Every click re-runs the script: services and the search index are built once in
  `@st.cache_resource`; the journey (checkpointer and model client) lives per browser session.
- The search box is an `st.form`, so the graph runs on submit, not per keystroke.
- A session's threads are swept after the TTL (EC-34).

## Requirements *(mandatory)*

- **P7-R01**: `app.py` and `ui/*` are the only modules importing `streamlit` (Principle IV).
- **P7-R02**: Pure view functions — grouping, the basket gate, the start-point options, the floor
  plate SVG — hold all logic, so they are tested without a browser; the Streamlit modules only
  lay them out.
- **P7-R03**: The floor plate is SVG drawn from the map's coordinates, scaled to the container
  width, with the route as a line, numbered stop markers in directions order, and a marker where
  the route changes floor.
- **P7-R04**: `verify` also checks that a reworded line keeps the words floor, aisle, rack and
  shelf of the fact line, so AC-27 holds with the model on.
- **P7-R05**: `LOCATOR_MODEL=off` forces the fallbacks — tests never reach GroqCloud, even with a
  key on the machine.

## Success Criteria *(mandatory)*

- **P7-SC1**: AC-08, AC-22, AC-27 pass headless (Streamlit `AppTest` and view tests).
- **P7-SC2**: AC-15 passes in headless Chromium at 390 × 844, locally and in CI.

## Assumptions

- A start point is the aisle end at the chosen aisle; the entrance is the default (FR-15).
- Playwright is a development dependency only; it is not deployed.
