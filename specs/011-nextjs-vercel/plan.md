# Implementation Plan: Next.js Page on Vercel (Phase 10)

**Branch**: `feature/nextjs` · **Spec**: `spec.md`

## Technical Context

- Page: Next.js 16.3.7, React 19.3.0, TypeScript 6.0.3 — pinned, each at least two weeks old.
  Static export (`output: "export"`): no server rendering is needed, and the CDN serves it.
- Barcode: zxing-wasm 3.1.4 — zxing-cpp compiled to WebAssembly, the same decoder Phase 9 ran
  on the server. The WASM file is copied to `public/` at build, not fetched from a CDN.
- API: FastAPI in `api/index.py`, Vercel's file-based Python function; `vercel.json` rewrites
  `/api/(.*)` to it and excludes the page, tests and docs from its bundle.
- Local and test serving: `LOCATOR_STATIC=out uvicorn api.index:app` — page and API in one
  process, so the browser tests need no Node server.

## Constitution Check

| Principle | Holds because |
|---|---|
| I. The model never supplies a fact | Unchanged graph; the page renders only verified views |
| II. Unknown is not false | Unchanged |
| III. Test-first, traced | Page tests ported to the API and the browser, each citing its ID |
| IV. One-way imports | Rule "web-only-in-api": fastapi/starlette/uvicorn only in `api/` |
| V. Every model call has a fallback | Unchanged; a spent cookie budget gives `NoModel` |
| VI. A store loads completely or not at all | Unchanged — at function start |
| VII. Kept simple | No database, no session store: the page carries the state; one function |

Technology constraints amended: constitution 1.4.0 (interface, deployment, secrets, phase 10).
