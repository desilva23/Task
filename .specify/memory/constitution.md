# Product Locator Constitution

The design documents in `docs/` are the specification this constitution governs:
`requirements.md` (what), `hld.md` and `lld.md` (how), `schema.md` (the data contract).
Spec Kit features under `specs/` plan and track work against them; they never restate or
override them.

## Core Principles

### I. The Model Never Supplies a Fact (NON-NEGOTIABLE)

Availability, location, distance, route order and every dietary or allergen claim MUST come
from the store data through deterministic code. A language model may interpret a request and
phrase an answer; it MUST NOT be the source of any fact the shopper sees.

- This is enforced in types, not prose. A model's output schema MUST contain no field in which
  a product name, SKU, location or distance could be invented (`ParsedQuery`), or MUST carry a
  value that is checked against a set the services built before it is used (`SubstituteChoice`).
- The `verify` node MUST sit on a plain, unconditional edge before the page renders. A composed
  answer that contradicts the service results is discarded and re-rendered from the template —
  never corrected in place.

Rationale: a hallucinated aisle sends a shopper to the wrong floor, and a hallucinated
"gluten free" can harm one. NFR-01, NFR-02, NFR-03; AC-10, AC-18, AC-25.

### II. Unknown Is Not False (NON-NEGOTIABLE)

A dietary flag has three states — `true`, `false` and unknown — and code MUST keep them apart
end to end. An empty cell is unknown. It MUST NOT be coerced to `false`, read with
`dtype=bool`, filled with `fillna(False)`, or tested for truthiness at a read site. An unknown
attribute MUST NOT satisfy a dietary requirement.

Rationale: collapsing unknown to false silently asserts a property about products nobody
checked. `schema.md` §2.2; NFR-03; AC-17, AC-25.

### III. Test-First, Traced to the Specification (NON-NEGOTIABLE)

Every phase begins by writing its tests from the specification, and those tests MUST fail
before the code that satisfies them is written.

- Every test MUST name the ID it proves — an `AC-`, `FR-`, `NFR-`, `C-` (constraint), `A-`
  (assumption), `EC-`, `V-` or `W-` identifier — in its name or docstring. A test that enforces this constitution itself rather
  than a requirement cites the principle instead: `CONST-I` … `CONST-VII`, or `CONST-SECRETS`
  for the secrets rule. The suite MUST reject a test that cites nothing, or an ID that is not
  defined.
- Code that no traced test exercises MUST NOT be merged.
- A test's expected values are taken from the specification. They MUST NOT be edited to make a
  failing implementation pass; if the specification is wrong, the specification is amended
  first and the test follows it.

Rationale: a requirement without a test is not finished being written (`requirements.md` §6),
and an implementation that rewrites its own oracle proves nothing.

### IV. A Deterministic Core Behind One-Way Imports

- `services/*` MUST NOT import `langgraph`, `langchain*`, `streamlit` or any model client.
- `graph/nodes/*` MAY import from `services/*`; `services/*` MUST NOT import from `graph/*`.
- Nothing below `ui/` and `app.py` MAY import `streamlit`.
- The graph's sequence MUST be expressed as explicit edges. A tool-calling agent that chooses
  which step runs next MUST NOT be introduced.

These rules MUST be checked mechanically in the test suite, not left to review.

Rationale: the deterministic half must be testable with no graph runtime and no model, which is
what makes Principle V provable; and the fixed order is what guarantees availability is checked
before a route is planned. `lld.md` §1, §6.

### V. Every Model Call Has a Fallback

Each of the three model-calling nodes (`understand_query`, `suggest_substitutes`,
`describe_route`) MUST have a named deterministic fallback, and the journey MUST complete with
a correct availability and a correct route when every model call fails. Each fallback taken
MUST be recorded in `degraded` and visible on the page.

Rationale: a model failure may cost fluency; it MUST NOT cost correctness. NFR-04; AC-11.

### VI. A Store Loads Completely or Not at All

A store folder MUST pass every refusal in `schema.md` §7 before the first search is served.
A failure MUST name the file, the row and the rule, and MUST stop the load; a half-loaded store
is never served. Warnings (W-) log and continue.

Rationale: the same bug found at load is a message to a data author; found at request time it is
a shopper walking the wrong way. NFR-07; AC-14.

### VII. Proof-of-Concept Scale, Kept Simple

Build what the specification requires and no more. No HTTP layer, no vector search, no
database, no message queue, no second store running concurrently. Distances are precomputed
once with all-pairs Dijkstra and looked up; search is BM25 with fuzzy fallback; ranking is a
lexicographic tuple sort, never a weighted sum.

Rationale: every one of these was weighed and settled in the HLD and `CLAUDE.md`. Re-opening one
requires amending the specification, not a pull request.

## Technology and Deployment Constraints

| Concern | Binding choice |
|---|---|
| Language | Python **3.12**, pinned, for the agent and the API; TypeScript for the page |
| Packaging | `uv` with a committed `uv.lock`; one dependency file only |
| Quality tools | `ruff` (lint + format), `pytest`; `hypothesis` where a property is clearer than an example |
| Orchestration | LangGraph (C-01), compiled once, called in-process |
| Interface | One Next.js page, a static export (C-03), calling a stateless FastAPI function under `/api`; store, index and matrices built once per function instance. `fastapi` is imported only in `api/` |
| Model provider | GroqCloud (C-06) through `langchain-groq`. Only models with **strict** structured-output support are permitted for schema-bound calls — at ratification, `openai/gpt-oss-20b` and `openai/gpt-oss-120b`. Model IDs live in configuration, never in code, and MUST be re-verified before Phase 6 |
| Routing maths | `scipy.sparse.csgraph.shortest_path`, method `D`, directed |
| Search | `rank_bm25`, `rapidfuzz` |
| Barcode decoding | zxing-wasm in the page, from live camera frames; retail symbologies only; the server re-checks the digits |
| Voice input | The browser's own speech recogniser (Web Speech API), only the words reach the API — no audio is sent to or stored by this system, and no model transcribes it |
| Data | Six CSVs per `schema.md`, synthetic only (C-04), produced by a seeded generator |
| Deployment | Vercel (C-07) — the page from the CDN, the API as one Python function |
| Stock alerts | AgentMail (C-09), from a GitHub Action; SDK only in the `alerts` dependency group; settings are repository secrets |

**Secrets.** The repository is public. `GROQ_API_KEY` MUST be supplied through
`.streamlit/secrets.toml` locally and a Vercel project environment variable when deployed. It is
read only by the Python function and never reaches the page. `secrets.toml` and `.env` MUST be gitignored,
and a test MUST fail if either is tracked.

**Public-deployment guard.** A deployed app spends the owner's key on behalf of anyone with the
URL. Model calls MUST be capped per visitor (a cookie count, since the API is stateless) and per
call (`max_tokens`), and a spend limit MUST
be set in the Groq console before the app is made public.

## Development Workflow and Quality Gates

**Order of authority.** `requirements.md` → `hld.md` / `lld.md` / `schema.md` → `specs/NNN-*/`.
A lower document that disagrees with a higher one is wrong.

**Phases.** Work proceeds bottom-up, one Spec Kit feature per phase:

| # | Phase | Proven by |
|---|---|---|
| 0 | Scaffold, toolchain, import-rule and secret-leak tests, traceability matrix | CI green |
| 1 | Seeded synthetic store generator and the store validator | AC-14, every V-rule |
| 2 | Services — catalogue, stock, planogram, store graph, route engine | AC-01, AC-04, AC-06, AC-07, AC-20, AC-21 |
| 3 | Multi-stop routing — floor order, open-path 2-opt, checkout | AC-05, AC-23, AC-24 |
| 4 | Search — classify, BM25, fuzzy, ranking, ambiguity | AC-02, AC-19, AC-26 |
| 5 | LangGraph — eleven nodes, interrupt, verify, fake model client | AC-03, AC-10, AC-11, AC-18 |
| 6 | GroqCloud in the three model nodes | AC-17, AC-25, NFR-04 |
| 7 | Streamlit page | AC-08, AC-15, AC-22, AC-27 |
| 8 | Portability store, performance, hostile input, deployment | AC-09, AC-12, AC-13 |
| 9 | Barcode scan — FR-03 reinstated by the owner | AC-28 |
| 10 | Next.js page and Vercel deployment — C-03 and C-07 changed by the owner | AC-15, AC-28, AC-13 |
| 11 | Stock alert emails to the store manager | AC-29 |
| 12 | Voice input — FR-27, brought into scope by the owner | AC-30 |
| 13 | Suggestions as you type (FR-28) and a one-screen page (NFR-11) — reviewers' input | AC-31, AC-15 |
| 14 | Review improvements — lists without commas, equally named products, pins, prices and tags, a kept basket, weak signal | AC-32 to AC-35 |
| 15 | Several stores — a five-floor store and a store switcher (FR-31, brought into scope by the owner) | AC-36, AC-09 |

**Gate.** A phase is complete only when all of its traced tests pass, `ruff` is clean, the
traceability matrix is updated, and the owner has reviewed it. The next phase MUST NOT start
before that review.

**Workflow per phase.** `/speckit-specify` → `/speckit-clarify` where anything is ambiguous →
`/speckit-plan` (its Constitution Check MUST pass) → `/speckit-tasks` → `/speckit-analyze` →
`/speckit-implement` → `/speckit-converge` until converged.

## Governance

This constitution supersedes any other working practice in this repository. An amendment MUST
be made by editing this file, MUST bump the version, and MUST update `CLAUDE.md` and any
specification document it affects in the same change.

Versioning is semantic: MAJOR for removing or redefining a principle, MINOR for adding one or
materially expanding guidance, PATCH for wording. Every `/speckit-plan` MUST record a Constitution
Check, and every gate review MUST confirm compliance with Principles I–VI before approval.

**Version**: 1.9.0 | **Ratified**: 2026-10-13 | **Last Amended**: 2026-10-16
