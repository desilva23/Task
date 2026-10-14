---
description: "Task list for Phase 9 — barcode scan"
---

# Tasks: Barcode Scan (Phase 9)

- [X] T001 Reinstate FR-03; add C-08, A-07, AC-28 and the barcode situations — `requirements.md`
- [X] T002 `hld.md` §3.5 and EC-48 to EC-54; EC-10 amended — spec first
- [X] T003 `lld.md` §1, §5, §6, §7, §8.5, §11, §14, §15; `schema.md` V-21 with the check digit
- [X] T004 Tests first: `tests/unit/test_barcode.py`, `tests/integration/test_scan.py`, page and V-21 tests
- [X] T005 `services/barcode.py`, `Catalogue.by_barcode`, V-21 check digit
- [X] T006 `action = "scan"` through `classify_query` and `resolve_items`; `Journey.run_scan`
- [X] T007 `ui/scan.py`; notices for runs that make no claim
- [X] T008 Browser test with a fake camera at 390 px
- [X] T009 Traceability matrix, `CLAUDE.md`, README; `scripts/check.sh` green; CI green

## Gate record (2026-10-14)

- `scripts/check.sh`: 418 passed, ruff clean. AC 28/28, FR 25/25, NFR 11/11 covered;
  EC-48 to EC-54 each have a test.
- AC-28 end to end in a real browser: Chromium's fake camera plays a frame showing the
  Coca-Cola Classic barcode; the photo is taken, decoded on the server, and the page shows the
  product in stock with "Add 1 available to basket", at 390 px with no sideways scroll
  (`phone-390-scan.png`).
- The decoder reads a rendered barcode tilted, soft, sideways and from a 6000 × 4000 photo; a
  blurred one is never read as a different code; a QR code holding the same digits is ignored.
- Found while building: a refused search (too short, digits only) held its message in state and
  the page never drew it — the shopper saw nothing. Fixed; such runs now show their message.
- Spec changes: FR-03 reinstated; C-08, A-07, AC-28; `hld.md` §3.5 and EC-48 to EC-54, EC-10
  amended; `lld.md` §8.5 and others; V-21 now checks the check digit; constitution 1.3.0
  (Phase 9 row, `zxing-cpp`). The two tests that kept FR-03 uncitable now prove the opposite.
- Not proven here: the camera on the deployed site and on a real phone — after merge, on the
  public URL (C-08).

## Superseded in part by Phase 10 (2026-10-14)

Phase 10 moved decoding from the server (a still photo through `zxing-cpp`) to the phone (live
frames through zxing-wasm), so `services/barcode.decode`, its photo tests and the `st.camera_input`
page are gone. The exact lookup, the digit checks, V-21 and AC-28 stand as built here.
