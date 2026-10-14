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
- [ ] T009 Owner: Vercel project, `GROQ_API_KEY`; check the branch preview; merge; retire Streamlit

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
