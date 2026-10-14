# Feature Specification: Barcode Scan (Phase 9)

**Feature Branch**: `feature/barcode-scan` · **Created**: 2026-10-14 · **Status**: Draft

**Input**: "Take another branch and implement a camera scanning module to scan the barcode of an
existing product." FR-03 was withdrawn during review; the owner reinstated it on 2026-10-14.
Proven by AC-28.

IDs here are local (`P9-…`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scan a product to find it (Priority: P1)

A shopper holding a product — or its empty packet brought from home — scans the barcode with the
phone camera and gets the same answer a typed search gives: availability, location and route.

**Acceptance Scenarios**:
1. **Given** a catalogued product's barcode in a photo, **Then** that exact product is returned
   with no choice prompt, its availability and location, and a route when it is in stock (AC-28).
2. **Given** a product the store has in the catalogue but sold out or not ranged, **Then** it is
   reported exactly as a typed search would report it (FR-08), with alternatives.
3. **Given** a scanned product, **Then** it can be added to the basket and routed like any other.

### User Story 2 - No camera, same lookup (Priority: P1)

**Acceptance Scenarios**:
1. **Given** the camera is declined, missing or cannot start, **When** the shopper types the
   digits under the barcode, **Then** the same product is returned (AC-28, EC-48).
2. **Given** mistyped digits, **Then** "That isn't a valid barcode" — never a nearest match (EC-52).

### User Story 3 - A barcode we do not have says so (Priority: P1)

**Acceptance Scenarios**:
1. **Given** a valid barcode that is not in this catalogue — another shop's product, a real
   product's barcode against the synthetic store — **Then** the page says it is not in this store's
   catalogue, with no nearest match and no suggestions (AC-28, EC-50).
2. **Given** a photo with no readable product barcode — blurred, damaged, a QR code — **Then**
   "No barcode found" with what to try (EC-49, EC-51). **Given** two different barcodes, **Then**
   neither is chosen (EC-53).

### Edge Cases

EC-48 to EC-54 (`hld.md` §6.7) and the amended EC-10.

## Requirements *(mandatory)*

- **P9-R01**: `services/barcode.py` checks digits (length, GS1 check digit) and decodes a photo
  with zxing-cpp, retail symbologies only. No lookup, no page, no framework import.
- **P9-R02**: `Catalogue.by_barcode` — exact, from a dictionary built once.
- **P9-R03**: A scan is a graph run with `action = "scan"`; `classify_query` checks the digits and
  a valid code goes to `resolve_items` without the model. No node is added.
- **P9-R04**: `Journey.run_scan(thread_id, code, start_node, step_free)`.
- **P9-R05**: The page has a "Scan a barcode" switch; only when on does it draw
  `st.camera_input`, plus a typed-digits form. Each photo is looked up once (EC-54).
- **P9-R06**: Messages from runs that make no claim (EC-01, EC-10, EC-52) are shown — they were
  held in state and never drawn.
- **P9-R07**: V-21 also checks the check digit.

## Success Criteria *(mandatory)*

- **P9-SC1**: AC-28 and EC-48 to EC-54 pass; every earlier test still passes; CI green.
- **P9-SC2**: In a real browser with a fake camera showing a catalogued barcode, the scan returns
  that product at 390 px with no horizontal scroll.

## Assumptions

- A still photo from `st.camera_input`, decoded on the server, is the proof-of-concept scan;
  live decoding needs a custom component (A-07).
- Streamlit Community Cloud serves HTTPS (C-08) and lets the app's frame use the camera.
- The synthetic barcodes are in GS1's `20` in-store range, so a real product scanned against the
  demo store is EC-50 — "not in this store's catalogue". That is the correct answer, not a fault.
