# Project context

Read this first. It carries the decisions and their reasoning from the session
that produced this repository, so they do not get re-litigated.

## What this is

A **proof of concept** for an in-store product finder and navigation agent.
A shopper types one or more products and gets, for each: whether it is
available, where it is (floor, aisle, rack, shelf), and the shortest walking
route to it, across floors. Built as an agentic system on synthetic data.

**Current state: design documents only. No code has been written yet.**

All four documents now exist. `docs/schema.md` is v1 and has no rendered page yet.

Sainsbury's is the reference retailer, but all data is synthetic and no real
retailer system is involved. The repository is **public** — keep anything
sensitive out of it.

## Document ownership — four documents, kept separate

This separation is deliberate and was asked for explicitly. Do not merge them.

| Document | Owns | Must not contain |
|---|---|---|
| `docs/requirements.md` | What the system must do. FR/NFR/AC/OQ register | Architecture, algorithms, schemas, technology choices beyond the stated constraints |
| `docs/hld.md` | Component architecture, search design, edge cases | Requirements (they live in requirements.md), field-level schemas |
| `docs/lld.md` | Module layout, signatures, algorithms, thresholds | Requirements, and the data schemas — §2 and §3 are now stubs pointing at `schema.md` |
| `docs/schema.md` | The six store CSVs, columns, identifier scheme, referential rules, load-time validation | Requirements, architecture, algorithms |

A requirement that names a technique cannot be challenged without re-opening the
design; a design hiding inside a requirement never gets reviewed. That is why
they are apart.

`docs/pages/*.html` are the rendered versions of these documents, published as
artifacts. **They duplicate the markdown and will drift.** Treat the markdown as
the source of truth and update the HTML alongside it, or stop maintaining the
HTML — but do not let them silently disagree.

Older documents (`proposed-scope.md`, `architecture.md`,
`use-case-understanding.md`, `clarifying-questions.md`,
`solution-sketch.md`, `genai-opportunities.md`) predate the four-document split
and still carry stale content. See **Pending work** below.

## Settled decisions — do not re-open without being asked

| Decision | Reasoning |
|---|---|
| **LangGraph** orchestrates the whole pipeline, including deterministic steps | Mandated. Deterministic steps become plain-function nodes; the generated graph is then the architecture diagram and cannot drift from code |
| **Streamlit**, calling the agent **in-process** | No HTTP layer exists. Removes the API surface and a day of plumbing. Reversible later because services carry no web dependency |
| **Dijkstra from every node at startup**, not per request | Layout is static, so all-pairs shortest paths precompute once; every query is an O(1) matrix lookup |
| **Not A\*** | It optimises a single query, and across floors straight-line distance is not an admissible heuristic — a route cannot pass through a ceiling |
| **BM25** for search, not vector search | At ~200 SKUs the structured filter handles semantic cases more cheaply and explainably. Hybrid BM25 + embeddings with reciprocal rank fusion is the scale-up path, not the starting point |
| **Lexicographic tuple sort** for ranking, not a weighted sum | A weighted sum cannot answer "why did this rank third" and can be mis-tuned into ranking an unstocked product first |
| **Three floors** for the demo, two for the portability store | Three is the smallest store where the fixed floor order is a real decision. Catalogue and planogram do not grow with floor count — only the map does |
| **Fixed floor order**, one picking pass per floor, ending at a checkout | A distance-only optimiser sends shoppers up and down repeatedly |
| **Basket gate** — batch results grouped by availability, one action moves only in-stock items | The basket, not the search result, is what gets routed, so no route is planned to an empty shelf |
| **Rack-level addressing**, graph stops at rack | A shelf is not somewhere you walk. ~300 nodes instead of ~1,200, and directions can still name a shelf |
| **Barcode entry is a camera scan**, not typed digits | A shopper holding the product has already found it, so typed entry was circular. The scan serves the packet-from-home and wrong-variant cases. Typed digits survive only as the degraded path when the camera is declined or unsupported, which keeps the all-digits query branch honest |
| **CSV** for the data files, map as two CSVs | Authorable in a spreadsheet, readable without a parser. A graph does not fit one table |

## The rule the whole design rests on

**The model interprets and phrases. It never supplies a fact.**

Locations, stock figures and distances come from the data via deterministic
code. A hallucinated aisle number sends a shopper to the wrong floor. Enforced
in types, not prose: `ParsedQuery` has no field for a product name, and a
substitute SKU outside the candidate set the service built is rejected.

Corollary: **allergen and dietary claims are never generated.** They come from a
recorded attribute, passed through verbatim. A `null` dietary flag means
*unknown*, never *absent* — collapsing null to false would silently assert "not
gluten free" about products nobody checked.

## Things not to do

- **Do not train a model on the store map.** It is a fact to look up, not a
  pattern to learn. A model that has "learned" the map invents aisle numbers for
  products it did not memorise. This is not a machine learning problem.
- **Do not use a ReAct agent that decides which tool to call.** The sequence is
  known; use explicit edges.
- **Do not promise the colleague-facing version.** It is out of scope and a
  different problem, not a later phase. Kept out of the requirements deliberately
  so it does not read as a commitment.
- **Do not put a schedule in the requirements document.** A timebox is a project
  fact, not a requirement, and cannot be tested.

## Known traps

| Trap | Why |
|---|---|
| `temperature=0` on the chat model | Rejected on current Claude models. Nearly every LangChain example passes it |
| `with_structured_output` + thinking | Known parse failure with thinking enabled, which is the default. Consider `method="json_schema"` |
| Streamlit re-executes the page per interaction | Graph, BM25 index and distance matrices must be in `@st.cache_resource`, or every click rebuilds them |
| Search box outside `st.form` | Every keystroke invokes the agent and the 5-second budget goes on unfinished queries |
| Textbook closed-tour 2-opt | Each floor leg is an **open** path with a fixed start; the wrap-around term must come out of the gain calculation |
| Abandoned clarifications | LangGraph does not expire threads. Without a TTL sweep every abandoned search leaks a checkpoint |
| `MemorySaver` vs `InMemorySaver` | Export name differs by release. Pin versions and check what is actually exported |

## Conventions

- Requirement IDs are stable. A resolved open question is **marked resolved, not
  deleted**, so decisions keep a trail.
- Every requirement has an acceptance criterion. One without is not finished.
- `notes/` is **gitignored** — internal notes stay out of this public repo. If
  that file is missing locally, it was never in git; ask the owner for it.

## Published pages

Private artifacts; source in `docs/pages/`. To update one from a new
conversation, pass its URL to the Artifact tool rather than publishing fresh.

- Requirements — https://claude.ai/artifact/3EX5yVGXaiUrGvMukseQbz
- HLD — https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB
- LLD — https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf
- Architecture note — https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C

## Pending work, in order

1. **Decide who owns startup validation.** `lld.md` §13 lists eleven checks and
   `schema.md` §7 lists forty-seven that supersede them. The rules are schema
   territory; *when they run* and `validation.py` are LLD territory. The likely
   answer is §13 becomes a pointer plus the lifespan ordering, but it is a
   judgement call, not a sweep. Nothing else in `schema.md` §10 is outstanding
   for the LLD except §11 and the edge count, which are items 3 and 4.
2. **Strip requirements out of `docs/hld.md` §1.** They live in
   `requirements.md` now.
3. **Remove the API contracts from `docs/lld.md` §11** and the `api/` directory
   from §1, replacing them with the Streamlit mechanics. No HTTP layer exists.
4. **Sweep the stale node and edge counts.** `schema.md` §8 derives 314 nodes
   and ~354 edge rows (~704 directed arcs) from a stated layout. The `~900
   edges` figure in `lld.md` §4, `architecture.md` §4 and `hld.md` §5 was never
   derived and is wrong. The ~300-node figure stands.
5. **Render and publish `docs/pages/locator-schema.html`**, if the HTML pages
   are being kept in step. The other three have artifacts; the schema has none.
6. **Then build**, if asked. Nothing has been implemented.
