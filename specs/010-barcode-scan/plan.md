# Implementation Plan: Barcode Scan (Phase 9)

**Branch**: `feature/barcode-scan` · **Spec**: `spec.md`

## Technical Context

Decoder: **zxing-cpp 3.1.1** — a self-contained wheel for Linux, macOS and Windows on Python 3.12,
so Streamlit Community Cloud needs no `packages.txt`. pyzbar was the alternative and needs the
`libzbar0` system package. Pillow (already present through Streamlit) is declared directly, since
`services/barcode.py` imports it.

Camera: `st.camera_input` (Streamlit 1.65) — a still photo, with a switch-camera button for the
rear camera on a phone. Drawn only behind a switch, because drawing it starts the camera.

## Constitution Check

| Principle | Holds because |
|---|---|
| I. The model never supplies a fact | A scan never reaches `understand_query`; the product is an exact lookup, and the answer passes `verify` like every other |
| II. Unknown is not false | A barcode not in the catalogue is reported as such — never mapped to the nearest product |
| III. Test-first, traced | Tests written first, citing FR-03, AC-28, EC-48–EC-54, V-21 |
| IV. One-way imports | `services/barcode.py` imports no framework; streamlit stays in `ui/` |
| V. Every model call has a fallback | No model call is added |
| VI. A store loads completely or not at all | V-21 now refuses a barcode with a bad check digit |
| VII. Kept simple | No node, no service, no live-decoding component; one library |

## Design

`hld.md` §3.5 and §6.7, `lld.md` §8.5 and §11, `schema.md` V-21.
