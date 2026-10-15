# Feature Specification: Suggestions and One Screen (Phase 13)

**Branch**: none — committed to `main` (owner's rule, 2026-10-14) · **Created**: 2026-10-16

**Input**: reviewers at the development-day demo — "while typing it should show suggested
items", and "if we scroll to see the content it is bad UX". The owner chose bottom tabs.
Proven by AC-31 and the amended AC-15.

## User Scenarios

1. **Given** "bre" typed, **Then** up to six products this store sells are listed, the breads
   first; choosing White Bread finds exactly it, with no question (AC-31).
2. **Given** "bananas, baked be", **Then** suggestions are for "baked be" only, and choosing one
   keeps "bananas, " (EC-67).
3. **Given** one letter, or "pepsi" (not sold here), **Then** no list; searching still answers as
   before (EC-65, EC-66). A sold-out product is listed, marked sold out.
4. **Given** the whole journey at 390 × 844 — search, basket, route, a step — **Then** the page
   never scrolls; only a long list or the map moves in its own frame (AC-15, NFR-11).

## Requirements

- **P13-R01**: `GET /api/store` carries every ranged product's label, terms, stock mark and
  popularity (`present.view.suggestions`).
- **P13-R02**: `lib/suggest.ts` and `components/SearchBox.tsx` — matched on the phone, a combobox.
- **P13-R03**: `app/page.tsx` — header, Search · Basket · Route panes, tab bar, sheets for the
  start point and the camera; `Results` as short cards; `Route` with a map frame and steps.

## Assumptions

- The map cannot shrink to one screen and stay legible (it is ~950 px tall at phone width), so
  it moves inside its own frame — the way any map does — opened on the step's rack.
