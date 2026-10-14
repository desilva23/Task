# Feature Specification: Next.js Page on Vercel (Phase 10)

**Feature Branch**: `feature/nextjs` (from `feature/barcode-scan`) · **Created**: 2026-10-14 ·
**Status**: Draft

**Input**: "Switch the UI to Next.js" — replacing the Streamlit page, deployed on Vercel, with
the barcode scan from Phase 9 carried over. The owner chose to replace Streamlit rather than run
both, and to build on the unmerged Phase 9 branch. C-03 and C-07 change; no FR, NFR or AC does.

IDs here are local (`P10-…`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The same journey, on a Next.js page (Priority: P1)

**Acceptance Scenarios**:
1. **Given** the page at 390 px, **Then** search, the basket gate, routing, the directions and
   the floor plates work as before, with no sideways scroll (AC-15, AC-08, AC-22, AC-27).
2. **Given** an ambiguous search, **Then** the choice is asked and answered (FR-05), though the
   server keeps nothing between the question and the answer.
3. **Given** anything the shopper types, **Then** it appears on the page only as text (AC-13).

### User Story 2 - A live scan (Priority: P1)

**Acceptance Scenarios**:
1. **Given** the camera pointed at a catalogued barcode, **Then** the product appears without a
   shutter tap, and the camera stops (AC-28, EC-54).
2. **Given** a QR code, two barcodes, or a declined camera, **Then** EC-51, EC-53 and EC-48 hold.
3. **Given** a scan, **Then** no image leaves the phone — only digits, which the server re-checks.

### User Story 3 - Deployed on Vercel for free (Priority: P1)

**Acceptance Scenarios**:
1. **Given** the owner's Vercel Hobby account, **Then** one project serves the page and the API,
   with the key in a Vercel environment variable only (C-07).

## Requirements *(mandatory)*

- **P10-R01**: `api/index.py` — FastAPI, four calls, stateless; failures are an apology.
- **P10-R02**: `Journey.answer` (search + answers per round) and `Journey.forget`.
- **P10-R03**: `present/` — the view as plain data, framework-free; `ui/` and `app.py` removed.
- **P10-R04**: The Next.js page — static export; React renders every string as text; the plates
  are the only inserted markup.
- **P10-R05**: Live decoding with zxing-wasm, served from our origin; the server-side photo
  decoder and its dependencies are removed.
- **P10-R06**: Model budget per visitor in a cookie; Groq spend limit and a firewall rate limit
  are the binding guards.
- **P10-R07**: `vercel.json`, `docs/deploy.md`, CI with Node; the import guard keeps the web
  framework in `api/`.

## Success Criteria *(mandatory)*

- **P10-SC1**: Every earlier test still passes or is ported; the browser suite runs the real page
  and API, including a live fake-camera scan; CI green.
- **P10-SC2**: The Vercel preview of the branch serves a working journey before merge.

## Assumptions

- Vercel's Python runtime installs from `pyproject.toml`/`uv.lock` on Python 3.12 and the
  function stays under the 500 MB limit (about 150–200 MB without Streamlit).
- A cookie budget is a courtesy limit; the owner sets the Groq spend limit.
