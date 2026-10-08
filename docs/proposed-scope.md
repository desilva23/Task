# Proposed Scope — One-Week Proof of Concept

**Deadline:** Friday. **Team:** one person. **Therefore:** one store, synthetic
data, no integrations.

This document is the one to put in front of the stakeholder. The others explain
the domain and the design; this one says what actually gets built, what
explicitly does not, and what we are assuming in the absence of answers.

## What this is

A working proof of concept that demonstrates the full user journey end to end:

> Search a product → see whether it's available → see exactly where it is →
> see the route to it on a store map.

It runs against **synthetic data shaped like a three-floor Sainsbury's
superstore**, orchestrated with **LangGraph**. The architecture and the
reasoning behind each decision are in `architecture.md`. It
proves the journey, the data model and the interface. It is not connected to
any real system, because connecting to real planogram and stock systems is a
procurement and integration exercise measured in months, not days.

**Say that explicitly on Friday.** A POC that is honest about being a POC is
credible. One that is mistaken for a pilot creates a promise you cannot keep.

## In scope

| Capability | What it does |
|---|---|
| Product search | Free-text search over a synthetic catalogue of ~150–200 SKUs |
| Availability | Stock count, treated as live and correct |
| Location | Floor, aisle, rack and shelf, from a synthetic planogram |
| Multiple locations | A SKU can appear on its home rack *and* on a promo end cap |
| Three floors | Non-food / ambient grocery / fresh, joined by two vertical cores |
| Position | Shopper picks their floor and aisle from a list |
| Single-product route | Shortest path — precomputed matrix lookup |
| Multi-product route | Optimal shopping route, fixed floor order, ending at the tills |
| NL query understanding | "something gluten free for lunchboxes" → structured filter |
| Out of stock handling | Suggest in-stock alternatives, dietary-filtered first |
| Clarification | Ambiguous query pauses the graph and asks the shopper |

## Explicitly out of scope

Name these out loud. An unstated omission looks like an oversight; a stated one
looks like judgement.

| Not building | Why | Where it lands |
|---|---|---|
| Real planogram integration | Needs a source system, access and a data contract | Phase 1 of a real build |
| Real stock integration | Same | Phase 1 |
| Multiple stores | Every store needs its own layout and planogram | Phase 2 |
| Indoor positioning (beacons, Wi-Fi) | Hardware rollout per store; manual aisle pick covers the demo | Phase 3, if ever |
| QR aisle markers | Cheap, but needs physical markers in a real store | Phase 2 |
| Shelf compliance vision | High value, but a project of its own | Separate initiative |
| Voice / hands-free | Only matters for the colleague version | Later |
| Native mobile app | Browser demo proves the journey at a fraction of the cost | Later |
| Turn-by-turn live navigation | Needs positioning first | Later |
| Login, accounts, loyalty | Nothing in the journey needs identity | Later |

## Assumptions register

Every one of these exists because a question in `clarifying-questions.md` is
unanswered. Put this table in front of the stakeholder — it converts "I didn't
know" into "I made a documented decision you can correct".

| # | Assumption | Replace when we learn |
|---|---|---|
| A1 | **Customer-facing**, shopper searching for themselves | Who the user is (Q1) |
| A2 | One synthetic store, 3 floors, ~36 aisles total | Store coverage (Q7) |
| A3 | Catalogue of ~150–200 SKUs is representative enough to demo | — |
| A4 | Floor order is fixed: highest floor with items first, then down to the tills | Confirmed by the lead |
| A5 | "Optimal" means shortest walking distance | Definition of optimal (Q12) |

Resolved since the first draft — no longer assumptions:

| Was | Now |
|---|---|
| Single product only | **Both** — single product and multi-product routes |
| Start position = entrance | Shopper **picks floor + aisle** |
| Aisle → bay → shelf | **Floor → zone → aisle → rack → shelf → facing** |
| Stock banded, staleness modelled | Stock **live and correct**, exact count shown |
| Route ends at last product | Route **ends at a checkout** |

## Proposed stack

Python backend, static frontend, no build step.

```
  backend/
    api.py              FastAPI — thin: validates, owns thread_id, streams
    graph.py            LangGraph StateGraph: nodes, edges, checkpointer
    nodes/
      understand.py       model — NL query → typed filter
      search.py           deterministic — filter → SKUs
      clarify.py          interrupt() — ask the shopper
      availability.py     deterministic — stock lookup
      substitutes.py      model — alternatives, dietary-filtered first
      locations.py        deterministic — planogram lookup
      routing.py          deterministic — matrix lookup / floor-clustered TSP
      describe.py         model — node list → directions
    services/
      catalogue.py  planogram.py  stock.py  graph_matrix.py
  data/
    store_graph.json    nodes + edges across 3 floors, incl. vertical cores
    planogram.json      SKU → floor/aisle/rack/shelf
    products.json       catalogue
    stock.json          stock positions
  frontend/
    index.html          search, floor+aisle picker, mode toggle, result card
    app.js              fetch + SSE node progress, no framework
    store-map.svg       three floor plates, aisles and racks as rectangles
```

Dependencies: `fastapi`, `uvicorn`, `langgraph`, `langchain-anthropic`,
`pydantic`, `scipy` (for the one all-pairs shortest-path call).

Why this shape:

- **No database.** JSON files loaded into memory at startup. The whole dataset
  is a few hundred kilobytes. A database adds setup cost and demonstrates
  nothing.
- **No frontend framework.** A search box, a result card and three SVG floor
  plates with a highlighted path. React would add a build step and no
  capability.
- **SVG store map.** Aisles and racks as labelled rectangles, one plate per
  floor, the route as a polyline. Deliberately schematic, which is honest — it
  is not a surveyed floor plan and shouldn't pretend to be.
- **LangGraph orchestrates the whole pipeline**, not only the model calls. The
  deterministic steps become plain-function nodes. See `architecture.md` for
  why, and for where that would tip into theatre.
- **Python** because the catalogue work, the graph precomputation, LangGraph and
  the Anthropic binding are all cleanest there.

## Build plan — six working days

| Day | Work | Done when |
|---|---|---|
| 1 | Synthetic data: 3-floor store graph with cores, planogram, catalogue, stock | A known SKU resolves to a known floor/aisle/rack in a JSON lookup |
| 2 | Service layer: catalogue, planogram, stock, keyword search | A plain function call returns SKU, count and full location |
| 3 | Routing: graph load, all-pairs matrix across floors, single-product lookup | Any aisle → any rack returns an ordered node list and a distance |
| 4 | LangGraph skeleton: state, the 6 deterministic nodes, conditional edges | `/journey` answers single-product end to end through the graph |
| 5 | Floor-clustered TSP + the 3 model nodes + the `clarify` interrupt | Multi-product route across floors, ending at the tills |
| 6 | Frontend: 3 floor plates, picker, mode toggle, route overlay, SSE progress | Can be demoed cold without explanation |

Sequencing rationale: the deterministic core is working by day 3 and the graph
answers end to end by day 4, with keyword search only. The model nodes and the
multi-product route are upgrades to something already working, so losing a day
still leaves a demo.

Risk to watch: day 5 carries both the TSP and the first model calls. If that
day slips, drop `suggest_substitutes` first — it is the least visible of the
three model nodes.

## Routing decision for the POC

All four tiers from `solution-sketch.md` are now in scope, because the lead
asked for both a single-product shortest path and an optimal multi-product
route.

- Floor/aisle/rack location answers most of the value on its own (Tier 0).
- Precompute all-pairs shortest paths across all three floors at startup, so
  every route query is a table lookup (Tier 2).
- Multi-product uses floor-clustered sequencing: fixed floor order, then
  nearest-neighbour + 2-opt within each floor, ending at the tills (Tier 3).

Still no A* and no runtime graph search. If asked: the layout is static, so
searching at request time is work we can do once at startup instead. Full
reasoning in `architecture.md`.

## Gen AI in the POC

Three model nodes out of nine, and **none of them is on the wire that returns a
location, a distance or a stock figure**:

| Node | Model | Why |
|---|---|---|
| `understand_query` | `claude-haiku-5-5` | High volume, simple task, latency-critical |
| `suggest_substitutes` | `claude-opus-5-5` | Needs real reasoning over constraints |
| `describe_route` | `claude-haiku-5-5` | Phrasing only; cacheable per node pair |

- Keyword search stays wired up as the fallback, so a model failure degrades
  the demo rather than breaking it.
- **Nothing generated asserts a location, a stock figure or a dietary claim.**
  The grounding rule from `genai-opportunities.md` holds even in a POC, because
  a hallucinated rack number in a live demo is the worst possible moment for
  one.

Everything else Gen AI could do here — shelf compliance from photos,
conversational basket building, voice — stays in `genai-opportunities.md` as
the roadmap, not the build.

## What to say about the gap

The question coming on Friday is "great, when can we have it in 600 stores?"
The honest answer, and a good one:

> The journey and the interface are proven. What stands between this and a real
> store is data, not software: a planogram feed with a contract and an owner, a
> stock feed with known freshness, and a machine-readable floor plan per store.
> The first of those is the long pole, and it's a conversation with the space
> planning team rather than an engineering task. Give me a real planogram
> extract and one real floor plan and I can tell you what a pilot store costs.

That reframes the next conversation onto the thing that actually decides
feasibility, and it is the most useful outcome Friday can produce.
