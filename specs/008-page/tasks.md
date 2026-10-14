---
description: "Task list for Phase 7 — the Streamlit page"
---

# Tasks: The Streamlit Page (Phase 7)

- [X] T001 Add `streamlit`, dev `playwright` + Chromium; confirm `st.html`, `AppTest`, `snapshot.interrupts`
- [X] T002 Write failing tests: `tests/unit/test_view.py` (AC-22, AC-27, start options, grouping, verify keeps location words), `tests/integration/test_page.py` (AC-08, FR-24, FR-05, C-04, degraded), `tests/browser/test_phone_width.py` (AC-15)
- [X] T003 Implement `ui/view.py`, `ui/floorplate.py`, `Journey.current`, verify location words
- [X] T004 Implement `ui/resources.py`, `ui/search.py`, `ui/results.py`, `ui/directions.py`, `app.py`
- [X] T005 CI installs Chromium; regenerate the matrix; `scripts/check.sh` green; screenshots for the gate

## Gate record (2026-10-14)

- `scripts/check.sh` green, including the headless-Chromium test. AC-08, AC-15, AC-22, AC-27
  proven; also FR-05, FR-15, FR-19, FR-20, FR-21, FR-22, FR-24, NFR-10, NFR-11, C-04.
- 390 × 844 screenshots: `phone-390.png` (results, basket, directions) and `phone-390-plate.png`
  (the floor plate) — regenerate with `LOCATOR_SCREENSHOTS=1 uv run pytest tests/browser`.
- Found while building: `st.html` drops inline SVG in Streamlit 1.65 (probed with a throwaway
  page); the plates render through `st.markdown(..., unsafe_allow_html=True)` — our own SVG from
  validated map data, text escaped. `st.columns` stacks below ~640 px, so the basket uses pills.
- Decisions for the owner:
  1. Each browser session holds its own `Journey` in session state (besides the thread IDs and
     basket the LLD lists) — that is what makes the model budget per session.
  2. `verify` also requires a reworded line to keep the words floor, aisle, rack and shelf
     (AC-27 with the model on).
  3. Floor changes are drawn as one arrow per core; the directions list names the connector.
  4. Theme colour teal (`.streamlit/config.toml`, committed; `secrets.toml` stays ignored).
