# Planogram-Based Product Locator

A shopper types one or more products — or scans a barcode with the phone camera — and
gets, for each, whether it is in stock,
exactly where it is — floor, aisle, rack and shelf — and the shortest walking route
to it across floors. A proof of concept on synthetic data, with Sainsbury's as the
reference retailer; no real retailer system is involved.

**Live:** https://find-it-in-store.vercel.app (Vercel — deployed from `main` on every push;
[`docs/deploy.md`](docs/deploy.md))

A Next.js page talks to a small stateless Python API (FastAPI); both deploy as one Vercel
project. The barcode is read on the phone, from the live camera; only the digits reach the server.

## How it works

LangGraph runs eleven steps on fixed edges. Eight are plain code: search (BM25
with a fuzzy retry), stock, locations, routing (all-pairs Dijkstra, a fixed floor
order, open-path 2-opt), and a verify gate. Three call a GroqCloud model, to read a
sentence, choose a safe substitute and word the directions, and each has a
deterministic fallback.

**The model interprets and phrases; it never supplies a fact.** Every location,
stock figure and distance comes from the store data, and `verify` re-checks every
claim against it before anything reaches the page.

## The documents

| Document | Owns | Page | Doc |
|---|---|---|---|
| [`docs/requirements.md`](docs/requirements.md) | What the system must do: 25 FR, 11 NFR, 28 AC | [page](https://claude.ai/artifact/3EX5yVGXaiUrGvMukseQbz) | [doc](https://claude.ai/code/artifact/c7a45740-2eb9-44ff-abcf-9463efd1cd0b) |
| [`docs/hld.md`](docs/hld.md) | Architecture, search design, barcode scan, interface, 54 edge cases | [page](https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB) | [doc](https://claude.ai/code/artifact/a9116252-bf28-42ef-9465-e28967d0db77) |
| [`docs/lld.md`](docs/lld.md) | Modules, state, node contracts, algorithms, configuration | [page](https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf) | [doc](https://claude.ai/code/artifact/96a1afa2-2ca7-4f5b-a10d-ce432489f37b) |
| [`docs/schema.md`](docs/schema.md) | The six store CSVs and the 43 refusals and 5 warnings checked at load | [page](https://claude.ai/artifact/AqRDBHcHJ97xXCxKS6TQzf) | [doc](https://claude.ai/code/artifact/abf938c6-faf9-4a5d-95f4-b6559cfe24b7) |

The pages and Docs are private; share them from their Share menu. Read in that
order. The rules for building against them are in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## How it was built

Eleven phases with GitHub Spec Kit, test-first, each reviewed at a gate. Every
phase's spec, plan, tasks and gate record is in `specs/`.

| Phase | Built | Spec |
|---|---|---|
| 0 | Scaffold and guard rails | [`specs/001-project-scaffold`](specs/001-project-scaffold) |
| 1 | Seeded store generator and validator | [`specs/002-store-data`](specs/002-store-data) |
| 2 | Services and route engine | [`specs/003-services`](specs/003-services) |
| 3 | Multi-stop routing and the basket | [`specs/004-multistop`](specs/004-multistop) |
| 4 | Search | [`specs/005-search`](specs/005-search) |
| 5 | The LangGraph pipeline | [`specs/006-graph`](specs/006-graph) |
| 6 | GroqCloud | [`specs/007-groq`](specs/007-groq) |
| 7 | The Streamlit page | [`specs/008-page`](specs/008-page) |
| 8 | Second store, performance, hostile input, deployment | [`specs/009-portability-deploy`](specs/009-portability-deploy) |
| 9 | Barcode scan — camera or typed digits, exact lookup | [`specs/010-barcode-scan`](specs/010-barcode-scan) |
| 10 | Next.js page, stateless API, Vercel | [`specs/011-nextjs-vercel`](specs/011-nextjs-vercel) |

[`docs/traceability.md`](docs/traceability.md) lists every requirement,
acceptance criterion, edge case and validation rule with the tests that prove it.
All 28 acceptance criteria are covered.

## Running it

Needs [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12 itself) and Node 20.9 or later.

```bash
uv sync --locked && npm ci    # both environments, from uv.lock and package-lock.json
npm run build                 # the page, as static files in out/
LOCATOR_STATIC=out uv run uvicorn api.index:app   # page and API on http://127.0.0.1:8000
scripts/check.sh              # lint, format check, the page build, every test
uv run pytest -m live         # live GroqCloud tests — needs the key, run on demand
```

While changing the page, run the API with `uv run uvicorn api.index:app --port 8000` and the
page with `npm run dev`; it proxies `/api/*` to the API.

For the model, put `GROQ_API_KEY = "…"` in `.streamlit/secrets.toml`, which is
gitignored. Without it the page runs on the deterministic wording.
`LOCATOR_STORE=data/SBY-PORT-002` serves the two-floor test store. Deploying:
[`docs/deploy.md`](docs/deploy.md).

After adding a test, regenerate the matrix with
`uv run python scripts/trace_matrix.py`; a stale matrix fails the check.

## Historical documents

Written on 2026-10-08, before the four documents were split out and before the
build. They are kept for their reasoning, and each opens with a note on what no
longer matches:
[`proposed-scope.md`](docs/proposed-scope.md) ·
[`architecture.md`](docs/architecture.md) ·
[`use-case-understanding.md`](docs/use-case-understanding.md) ·
[`clarifying-questions.md`](docs/clarifying-questions.md) ·
[`solution-sketch.md`](docs/solution-sketch.md) ·
[`genai-opportunities.md`](docs/genai-opportunities.md).
