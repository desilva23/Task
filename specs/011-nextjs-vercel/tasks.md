---
description: "Task list for Phase 10 — Next.js page on Vercel"
---

# Tasks: Next.js Page on Vercel (Phase 10)

- [X] T001 Amend C-03, C-07, A-07; `hld.md` §1, §2, §3.5, §4, §4.1, EC-34/36/41/49/53/54 — spec first
- [X] T002 `Journey.answer`, `Journey.forget`; `present/` from `ui/`; remove `app.py`, `ui/`, Streamlit
- [X] T003 `api/index.py`; API tests (`tests/integration/test_api.py`); hostile tests on the API
- [X] T004 The Next.js page: position, search, scan, clarification, results, basket, route, plates
- [X] T005 Live decoding with zxing-wasm; server-side photo decoding removed
- [X] T006 Browser tests at 390 px with Chromium's fake camera
- [X] T007 `vercel.json`, `docs/deploy.md`, CI with Node, `scripts/check.sh` builds the page
- [X] T008 `lld.md` §1, §8.5, §11, §13, §14, §15, §16; constitution 1.4.0; CLAUDE.md, README
- [X] T009a Vercel project `find-it-in-store` created and deployed from `feature/nextjs`
- [X] T009b #4 and #5 merged to `main` on the owner's word (2026-10-14); production follows `main`
- [X] T009c Owner added `GROQ_API_KEY` in Vercel (2026-10-15); live: "something for a headache" → Medicines options in ~1 s, browser suite 8/8 with the model on
- [X] T009d Owner deleted the Streamlit app (2026-10-15)

## Gate record (2026-10-14)

- `scripts/check.sh`: ruff clean, `next build` (type check) clean, 417 tests pass. AC 28/28,
  FR 25/25, NFR 11/11; edge cases 41/54 (was 40 — EC-41 now has a test).
- Browser suite on the real page and API at 390 px, 8 tests: the full three-floor journey; the
  clarification; typed markup shown as text with no element or dialog created; **a live scan from
  Chromium's fake camera, with no shutter tap, and the camera stopped after the read**; a QR code
  ignored; two barcodes refused; camera declined → typed digits; a refresh keeps the basket.
- The API keeps nothing between requests: a test watches every journey a request builds and
  finds its checkpoint storage empty afterwards.
- Screenshots: `phone-390-route.png`, `phone-390-scan.png`.
- Not yet proven: the Vercel deployment itself (T009) — it needs the owner's account.

## Deployment record (2026-10-14)

- Project `find-it-in-store` on the owner's Vercel Hobby account, linked to `desilva23/Task`;
  first deployment from `feature/nextjs` (commit 373e880): https://find-it-in-store.vercel.app
- Build: Next.js 16.3.7 static export; Python 3.12 from `.python-version`, dependencies from
  `uv.lock`; function bundle 228 MB (limit 500 MB). Build 32 s.
- The browser suite against the live site: **8 passed**, including the scan from Chromium's fake
  camera. Warm `/api/search` for three items: 0.33–0.36 s.
- No `GROQ_API_KEY` yet, so answers use the plain wording — the owner adds the key.
