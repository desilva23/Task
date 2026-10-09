# Planogram-Based Product Locator

Design pack for an in-store product search, location and navigation use case,
with Sainsbury's as the reference retailer.

**Scope: a one-week proof of concept, built by one person, on synthetic data.**
Not a programme. The design is right-sized for that, and
[`docs/proposed-scope.md`](docs/proposed-scope.md) is explicit about what is in,
what is out, and what is being assumed.

**Rendered pages:**
· [High-level design](https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB) — requirements, search design, basket gate, edge cases
· [Low-level design](https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf) — schemas, node contracts, algorithms, API
· [Architecture note](https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C) — LangGraph graph, store model, routing

---

## The use case in one paragraph

A user searches for a product in a store. The system shows whether it is
available, where it is (aisle, bay, shelf), and the optimal route to reach it.
Four kinds of data are needed to do that — a product catalogue, a stock
position, planogram location data, and a store floor layout. In a real build
those are four separate upstream systems, and obtaining them is the project.
For the proof of concept all four are synthetic, which is what makes a week
realistic.

## The three things worth knowing

**1. The hard part is data, not algorithms.** Routing is close to free — the
store layout is static, so shortest paths across all three floors are
precomputed once at startup and every route query becomes a table lookup. There
is no runtime pathfinding and no need for A*. What actually decides feasibility
is whether machine-readable planogram and floor-plan data exist. No public
dataset holds a multi-floor supermarket planogram at rack level, so the POC's
store map is authored.

**2. A planogram says where a product is *supposed* to be.** Shelves drift from
plan within days of a range change. In a POC this doesn't bite, because the
data is synthetic and therefore perfect. In a real build it is the single
biggest risk, and it needs either a compliance signal or a user "this is wrong"
feedback loop.

**3. Who the user is changes everything.** A shopper finding one product and a
colleague picking a 60-item online order share a data layer and nothing else —
the second is a route-sequencing problem, not a shortest-path one. The POC
assumes a shopper; that assumption is the first one to get corrected.

## Gen AI, briefly

One use in the POC: **turning how people actually phrase a search** ("something
gluten free for lunchboxes") into a structured catalogue filter. One call, with
keyword search as the fallback.

The rule that matters: **the model interprets and explains, it never supplies
facts.** Locations, stock and routes come from the systems of record. A
hallucinated aisle number sends a shopper to the wrong aisle, and a
hallucinated dietary claim is considerably worse than that.

The larger opportunity — vision models reading shelf photos to detect where
reality has drifted from the planogram — is the roadmap item worth raising,
because it is the only real answer to point 2 above.

---

## Reading order

| # | Document | What it covers |
|---|---|---|
| 1 | [`docs/proposed-scope.md`](docs/proposed-scope.md) | **Start here.** The POC definition, in/out of scope, assumptions register, stack, six-day build plan |
| 1b | [`docs/hld.md`](docs/hld.md) | **The review document.** Consolidated requirements register, the search design, 46 edge cases, and answers to the questions most likely to be asked |
| 1c | [`docs/lld.md`](docs/lld.md) | Low-level design: identifier scheme, file schemas, graph state, node contracts, search and routing internals, API contracts, startup validation, test plan |
| 1d | [`docs/architecture.md`](docs/architecture.md) | The LangGraph graph spec, three-floor store model, routing design, and every decision with its reasoning |
| 2 | [`docs/use-case-understanding.md`](docs/use-case-understanding.md) | What a planogram is, the use case decomposed, and the customer vs. colleague split |
| 3 | [`docs/clarifying-questions.md`](docs/clarifying-questions.md) | Questions for the stakeholder, prioritised, each with why it matters |
| 4 | [`docs/solution-sketch.md`](docs/solution-sketch.md) | Data model, store graph, the tiered routing answer, API shape, risks |
| 5 | [`docs/genai-opportunities.md`](docs/genai-opportunities.md) | Where Gen AI fits, where it must not be used, guardrails |

For the Friday conversation, documents 1, 1b and 3 are the ones that matter:
here is what I'm building, here is how it's put together, here is what I
assumed, and here is what I need from you.
