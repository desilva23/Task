---
description: "Task list for Phase 8 — portability, performance, hostile input, deployment"
---

# Tasks: Portability, Performance, Hostile Input, Deployment (Phase 8)

- [X] T001 Amend `schema.md` §8 to the portability store as designed (125 nodes, 140 edges) — spec first
- [X] T002 Parametrise the map builder (demo byte-identical); `datagen/port.py`; `--store port`; commit `data/SBY-PORT-002`
- [X] T003 `tests/acceptance/test_acceptance.py` — AC-01 to AC-08 on both stores, model on and off (AC-09)
- [X] T004 `tests/acceptance/test_performance.py` and a live timing test (AC-12)
- [X] T005 `tests/acceptance/test_hostile.py` (AC-13); `MAX_QUERY_CHARS`; markdown escaping; page apology; error details off
- [X] T006 Deployed-URL mode for the browser test; `docs/deploy.md`
- [X] T007 Owner deploys to Streamlit Community Cloud; run the browser test and a smoke journey on the public URL

## Gate record (2026-10-14)

- `scripts/check.sh`: 387 passed, ruff clean. **Every AC (27/27), FR (24/24) and NFR (11/11)
  now has a proving test** — `docs/traceability.md`.
- AC-09: the same 26 checks (AC-01 to AC-08 × two stores × model on/off) pass on
  `SBY-PORT-002` — two floors, 5-rack aisles, shared aisles, four tills — with no code change.
- AC-12: in-process median 3 ms (one product) and 6 ms (ten); **live GroqCloud: one product
  0.5–0.6 s, ten products under 1 s** — against 5 s and 10 s.
- AC-13: 18 hostile inputs (the §7 list plus markup, path, query, template and null-byte probes)
  — no error page, path, traceback, secret, live link or changed tool; an internal failure shows
  an apology.
- Found while building: the page rendered shopper text and model wording through markdown, so a
  typed `[link](…)` or `![](…)` would have rendered live — everything shown is now escaped.
- Spec changes: `schema.md` §8 portability sizes (143/160 could not come from this topology;
  now 125/140); `MAX_QUERY_CHARS` 1000 in `lld.md` §14; the Phase 4 EC-06 test follows the
  amended spec (the length cap now applies before the 30-item cap).
- Open for the owner: deploy (`docs/deploy.md`), Groq tier and spend limit.

## Deployment record (2026-10-14)

- Deployed by the owner to Streamlit Community Cloud: https://weurhd8vy4j68dmbhcbkd6.streamlit.app
  (branch `claude/planogram-store-navigation-czn7bh`, `app.py`, Python 3.12, key in Cloud
  secrets only).
- Live smoke journeys with GroqCloud: "Coca-Cola Classic" → in stock, floor 1 aisle 7 rack 3
  shelf 2, verified route with model wording; "I need something for a headache please" → the
  Medicines options, 2.3 s.
- AC-15 on the public site: `LOCATOR_URL=…/~/+/ uv run pytest tests/browser` passed at 390 px;
  the Cloud wrapper page does not scroll sideways either.
- Still the owner's: Groq tier and spend limit.
