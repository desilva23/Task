# Implementation Plan: The Streamlit Page (Phase 7)

**Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

## Summary

One Streamlit page in `app.py`, laid out by thin `ui/*` modules over pure view functions in
`ui/view.py` and `ui/floorplate.py`. Services are cached once per process; each browser session
owns a `Journey` (checkpointer + model client with its call budget). Session state holds the
thread IDs and the basket draft only; everything else is read back from the checkpoint.

## Technical Context

Python 3.12 · `streamlit` 1.65 (C-03) · tests: `streamlit.testing.v1.AppTest` headless, Playwright
headless Chromium for the 390 px check (dev dependency only, installed in CI).

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | The page shows only verified state; nothing is composed in the UI | ✅ |
| II | Dietary status shown only as the verified statement has it | ✅ |
| III | AC-08, AC-15, AC-22, AC-27 tests first | ✅ |
| IV | Only `app.py` and `ui/*` import streamlit — enforced by the Phase 0 test | ✅ |
| V | `degraded` surfaced on the page | ✅ |
| VII | One page, in-process, no HTTP layer | ✅ |

## Project Structure

```text
app.py               the page
ui/resources.py      cached services; per-session Journey; LOCATOR_MODEL=off
ui/view.py           start options, result grouping, basket gate (pure)
ui/floorplate.py     floor plate SVG and route segments (pure)
ui/search.py · ui/results.py · ui/directions.py   Streamlit layout only
graph/journey.py     + current(thread_id): read a run back from its checkpoint
tests/unit/test_view.py · tests/integration/test_page.py · tests/browser/test_phone_width.py
```
