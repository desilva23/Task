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

It runs against **synthetic data shaped like a Sainsbury's superstore**. It
proves the journey, the data model and the interface. It is not connected to
any real system, because connecting to real planogram and stock systems is a
procurement and integration exercise measured in months, not days.

**Say that explicitly on Friday.** A POC that is honest about being a POC is
credible. One that is mistaken for a pilot creates a promise you cannot keep.

## In scope

| Capability | What it does |
|---|---|
| Product search | Free-text search over a synthetic catalogue of ~150–200 SKUs |
| Availability | In stock / low stock / out of stock, from a synthetic stock file |
| Location | Aisle, bay and shelf, from a synthetic planogram |
| Multiple locations | A SKU can appear in its home bay *and* on a promo end cap |
| Route | Entrance → product, drawn on a simple store map, with distance |
| Shopping list | Several items in serpentine aisle order, one combined route |
| NL query understanding | "something gluten free for lunchboxes" → structured filter |
| Out of stock handling | Suggest in-stock alternatives from the same category |

## Explicitly out of scope

Name these out loud. An unstated omission looks like an oversight; a stated one
looks like judgement.

| Not building | Why | Where it lands |
|---|---|---|
| Real planogram integration | Needs a source system, access and a data contract | Phase 1 of a real build |
| Real stock integration | Same | Phase 1 |
| Multiple stores | Every store needs its own layout and planogram | Phase 2 |
| Indoor positioning (beacons, Wi-Fi) | Hardware rollout per store | Phase 3, if ever |
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
| A2 | Single product at a time, with a shopping list as a bonus | Single vs. list (Q6) |
| A3 | One superstore, ~15 aisles, synthetic layout | Store coverage (Q7) |
| A4 | Start position is always the **entrance** | Positioning (Q4) |
| A5 | Location granularity is aisle → bay → shelf | Planogram granularity (Q2) |
| A6 | Availability is **shelf stock**, shown as a band not a number | Availability definition (Q5) |
| A7 | "Optimal" means shortest walking distance | Definition of optimal (Q12) |
| A8 | Catalogue of ~150–200 SKUs is representative enough to demo | — |

## Proposed stack

Python backend, static frontend, no build step.

```
  backend/            FastAPI
    api.py              one orchestrating endpoint for the UI
    search.py           catalogue search + NL query understanding
    locations.py        planogram lookup
    availability.py     stock lookup
    routing.py          store graph + precomputed distance matrix
  data/
    store_layout.json   nodes and edges for one store
    planogram.json      SKU → aisle/bay/shelf
    products.json       catalogue
    stock.json          stock positions
  frontend/
    index.html          search box, result card, SVG store map
    app.js              fetch + render, no framework
    store-map.svg       hand-drawn floor plan, aisles as rectangles
```

Why this shape:

- **No database.** JSON files loaded into memory at startup. The whole dataset
  is a few hundred kilobytes. A database adds setup cost and demonstrates
  nothing.
- **No frontend framework.** A search box, a result card and an SVG with a
  highlighted path. React would add a build step and no capability.
- **SVG store map.** Aisles as labelled rectangles, the route as a polyline.
  Looks deliberately schematic, which is honest — it is not a surveyed floor
  plan, and shouldn't pretend to be.
- **Python** because the catalogue work, the graph precomputation and the
  Anthropic SDK are all cleanest there, and it keeps the whole thing in one
  language.

## Build plan — six working days

| Day | Work | Done when |
|---|---|---|
| 1 | Synthetic data: store layout graph, planogram, catalogue, stock | A known SKU resolves to a known bay in a JSON lookup |
| 2 | Location + availability + plain keyword search services | `/search?q=coke` returns SKU, band and aisle/bay |
| 3 | Routing: graph load, precomputed all-pairs matrix, route lookup | Entrance → any bay returns an ordered node list and a distance |
| 4 | NL query understanding (one structured-output call) | "gluten free lunchbox snacks" returns sensible real SKUs |
| 5 | Frontend: search, result card, SVG map with the route drawn | Full journey clickable in a browser |
| 6 | Shopping list mode, out-of-stock alternatives, polish, demo script | Can be demoed cold without explanation |

Sequencing rationale: the journey works end to end by day 3 with plain keyword
search. Everything after that is an upgrade to something already working, so if
a day is lost there is still a demo.

## Routing decision for the POC

Build **Tier 0, 1 and 2** from `solution-sketch.md`, skip Tier 3.

- Aisle/bay location is the answer to most of the value (Tier 0).
- Serpentine aisle-order sort handles the shopping list (Tier 1).
- Precompute all-pairs shortest paths at startup — a few hundred nodes is
  instant — so every route query is a table lookup (Tier 2).
- Skip TSP sequencing. With a demo list of 5–8 items, serpentine order is
  indistinguishable from optimal, and nobody watching can tell the difference.

No A*, no runtime graph search. If asked, the answer is: the layout is static,
so searching at request time is work we can do once at startup instead.

## Gen AI in the POC

One use, not nine: **natural-language query understanding**. A single
structured-output call turns a messy query into a catalogue filter, then
deterministic search does the rest. The model never names a product.

- `claude-haiku-5-5` — the volume is high, the task is simple, and it is
  $0.10 / $0.50 per million tokens, so the demo costs pennies.
- Keyword search stays wired up as the fallback, so a model failure degrades
  the demo rather than breaking it.
- **Nothing generated asserts a location, a stock figure or a dietary claim.**
  The grounding rule from `genai-opportunities.md` holds even in a POC, because
  a hallucinated aisle number in a live demo is the worst possible moment for
  one.

Everything else Gen AI could do here — shelf compliance from photos,
conversational basket building, voice — is in `genai-opportunities.md` as the
roadmap, not the build.

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
