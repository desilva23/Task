# Where Gen AI Belongs in the Planogram Locator

> **In the one-week POC, only item 1 below gets built** — natural-language
> query understanding, one structured-output call, with keyword search as the
> fallback. Everything else here is the roadmap: worth raising on Friday to
> show where this goes, explicitly not worth building this week. See
> `proposed-scope.md`.
>
> The grounding rule and the allergen guardrail below apply in the POC too.
> A hallucinated aisle number is at its most damaging during a live demo.

## First, the framing that will survive the stakeholder meeting

Do not walk in and say "I want to use Gen AI in this". That reads as a solution
looking for a problem, and a lead who asked for a product locator will hear
scope creep.

Walk in with the two weaknesses of the classic design, and let the AI be the
answer to them:

1. **Keyword search fails on how people actually talk.** Real queries are
   "something for a hangover", "nappies for a 9 month old", "that gluten free
   bread", "paracetomol" (misspelled). A keyword index over a product
   catalogue returns nothing useful for any of those.
2. **Planogram data decays and nobody notices.** Shelves drift from plan within
   days of a range change. We flagged this as the project's biggest risk. There
   is no cheap non-AI fix for it.

Gen AI addresses both directly. That is the pitch — two named problems, not a
technology preference.

## The single most important design rule

**The model interprets and explains. It never supplies facts.**

Product location, stock levels and routes come from systems of record via tool
calls. The model's job is to understand what the user meant, call the right
tools, and phrase the answer. If the model ever states an aisle number it did
not receive from a tool result, the feature is broken — and a confidently wrong
"Aisle 12" is worse than no feature at all, because the shopper walks to
aisle 12.

Every factual claim in a response must trace back to a tool result. Design for
that from the first line of code.

---

## Where Gen AI genuinely earns its place

Ranked by value delivered against effort.

### 1. Natural-language query understanding — highest value, lowest risk

The model converts a messy query into a structured catalogue query, then
deterministic retrieval does the rest.

```
"something gluten free for the kids' lunchboxes"
  ↓ model
{ "category": ["snacks", "bakery"],
  "dietary": ["gluten_free"],
  "attributes": ["single_portion", "ambient"],
  "exclude_allergens": [] }
  ↓ deterministic catalogue search
real SKUs, real locations, real stock
```

This is a single structured-output call. Use **structured outputs**
(`output_config: {format: {...}}`) so the result is schema-valid every time and
you are not regex-parsing prose. Cheap, fast, and the model cannot invent a
product because it never names one — it only describes what to look for.

### 2. Shelf compliance from photos — fixes the decay problem

A colleague (or a fixed camera, or a shelf-scanning unit) photographs a bay.
A vision model reads the shelf and compares it against the planogram:

- which SKUs are actually present
- gaps / out-of-shelf
- products in the wrong place
- shelf-edge label mismatches

This is what closes the loop on "planogram ≠ reality" and it is the highest-ROI
AI application in the whole programme — it improves every other feature by
making the location data true.

**Be honest about maturity:** production-grade shelf recognition at retail scale
is normally a *trained detector* (specialised CV), not a general-purpose vision
model. But a vision model is dramatically cheaper and faster to stand up, and is
well suited to **triage** — flag the bays that look wrong and send a human or a
specialised model at those. Pitch it as triage, not as a replacement for a
trained detector, and you will be believed.

### 3. Conversational basket building — the commercial upside

```
"I'm making a lasagne for six"
  → generates the ingredient list
  → resolves each to a real SKU in this store
  → one optimised route covering all of them
```

This turns a locator into a basket-builder, which is the version with a revenue
story attached (basket size uplift), not just a cost-saving one. Worth raising
even if it's out of scope, because it changes how the project gets funded.

### 4. Out-of-stock substitution with reasoning

When something is unavailable, the model proposes alternatives *and explains
why* — same use, same dietary profile, similar price. Better than a static
substitution table because it can reason about the shopper's actual constraint.
A dead end becomes a sale.

**Safety caveat, non-negotiable:** see Allergens below.

### 5. Natural-language wayfinding

Turn a graph path into human directions using landmarks:

> "Walk past the bakery, turn left at the end of the home baking aisle. It's on
> your right at eye level, next to the passata."

Cheap polish, and it makes the route feel like a person gave it. **Pre-generate
and cache these per node-pair or per bay** — do not generate live on every
request. The phrasing for "entrance → aisle 7 bay 3" doesn't change between
shoppers.

### 6. Bootstrapping the data we don't have

Multimodal models can read PDF/CAD floor plans and planogram diagrams to
produce a first-draft store graph and location table, with a human verifying.
This attacks the hidden cost we flagged — manually digitising hundreds of
stores. It won't be perfect; "90% correct draft plus human review" is still
transformative against "start from a blank page per store".

### 7. Catalogue enrichment — offline, boring, very effective

Batch job over the product catalogue generating synonyms, colloquial names
("coke", "nappies", "kitchen roll"), dietary tags and search terms from product
descriptions and images. Massively improves search recall. Low risk because it
is offline, reviewable, and run once per catalogue change.

Run this through the **Batch API** at 50% cost — it is not latency-sensitive.

### 8. Hands-free colleague assistant

Pickers have both hands on a trolley. Speech-to-text → model → text-to-speech:
"where's the next item", "mark that one short". This is where a colleague-facing
version gets its real productivity gain.

### 9. Accessibility

Rich verbal descriptions of location and route for visually impaired shoppers.
Falls out almost free from (5), and for a UK retailer accessibility is a legal
consideration rather than a nice-to-have.

---

## Where NOT to use Gen AI

Say these out loud in the meeting. Knowing where *not* to use it is what makes
the rest credible.

| Don't | Why | Use instead |
|---|---|---|
| Compute the route with an LLM | It will hallucinate aisle numbers and it's slower and more expensive than the exact answer | A* / Dijkstra on the store graph. Let the model *phrase* the route, not find it |
| Ask the model where a product is | Training data has no knowledge of this store's shelves | Tool call to the location service |
| Ask the model what's in stock | Same, plus stock changes by the minute | Tool call to the stock service |
| Report stock numbers through the model | Numeric drift is a real failure mode and the exact number is already wrong | Pass the band through verbatim from the tool result |
| Fine-tune first | Expensive, slow to iterate, and almost never the bottleneck | Prompting + retrieval + structured outputs. Revisit only with evidence |

---

## Architecture: tool-calling over deterministic services

The right shape is a **grounded tool-use loop**. The model gets tools, not data:

```
                   ┌──────────────────────────────────┐
   user query ───► │  Claude (intent + orchestration) │
                   └──────────────┬───────────────────┘
                                  │ tool calls
        ┌────────────┬────────────┼────────────┬──────────────┐
        ▼            ▼            ▼            ▼              ▼
   search_        check_      get_         compute_      suggest_
   products    availability  locations      route      substitutes
        │            │            │            │              │
        ▼            ▼            ▼            ▼              ▼
    catalogue     stock      planogram    store graph    catalogue
     (system of record — every fact in the answer comes from here)
```

Tool definitions, sketched:

```json
[
  { "name": "search_products",
    "description": "Search the product catalogue for this store. Returns real SKUs only.",
    "strict": true,
    "input_schema": {
      "type": "object",
      "properties": {
        "query":    { "type": "string" },
        "category": { "type": "array", "items": { "type": "string" } },
        "dietary":  { "type": "array", "items": { "type": "string" } },
        "limit":    { "type": "integer" }
      },
      "required": ["query"],
      "additionalProperties": false
    }},

  { "name": "check_availability",
    "description": "Current stock position for SKUs in this store. Shelf stock, not back-room.",
    "strict": true,
    "input_schema": {
      "type": "object",
      "properties": {
        "store_id": { "type": "string" },
        "skus":     { "type": "array", "items": { "type": "string" } }
      },
      "required": ["store_id", "skus"],
      "additionalProperties": false
    }},

  { "name": "get_locations",
    "description": "Planogram locations for a SKU. May return several (home bay, promo end cap).",
    "strict": true,
    "input_schema": {
      "type": "object",
      "properties": {
        "store_id": { "type": "string" },
        "sku":      { "type": "string" }
      },
      "required": ["store_id", "sku"],
      "additionalProperties": false
    }},

  { "name": "compute_route",
    "description": "Optimal path over the store graph. Deterministic — the model must not compute routes itself.",
    "strict": true,
    "input_schema": {
      "type": "object",
      "properties": {
        "store_id":  { "type": "string" },
        "from_node": { "type": "string" },
        "to_nodes":  { "type": "array", "items": { "type": "string" } },
        "step_free": { "type": "boolean" }
      },
      "required": ["store_id", "from_node", "to_nodes"],
      "additionalProperties": false
    }}
]
```

Implementation notes that matter:

- Set **`strict: true`** on every tool so arguments are schema-valid and you
  never hand a malformed SKU to a downstream service.
- Use the SDK's **tool runner** rather than hand-writing the request → execute →
  loop cycle; its per-turn hooks are where you put logging, approval gates and
  latency budgets.
- Return `tool_result` with `is_error: true` on a downstream failure — don't
  silently drop it, or the model will fill the gap with a guess.
- The **store context** (store id, aisle list, category map, system prompt) is
  stable per store. Put it first in the prompt and cache it; put the user's
  query after the last cache breakpoint. Verify it's working by checking
  `usage.cache_read_input_tokens` is non-zero — if it's zero, something
  volatile (a timestamp, unsorted JSON) is silently invalidating the prefix.

### Model selection

| Job | Model | Why |
|---|---|---|
| Intent parsing / query → structured filter | `claude-haiku-5-5` ($0.10 / $0.50 per MTok) | High volume, low complexity, latency-critical. Effort `low` |
| Conversational basket building, substitution reasoning | `claude-opus-5-5` ($4 / $20 per MTok) | Needs real reasoning over constraints |
| Shelf compliance triage | `claude-haiku-5-5`, escalating ambiguous bays to `claude-opus-5-5` | Volume is enormous; see cost note below |
| Offline catalogue enrichment | `claude-haiku-5-5` via Batch API | 50% cost, no latency requirement |

Use adaptive thinking (`thinking: {type: "adaptive"}`) for the reasoning-heavy
paths and `output_config: {effort: "low"}` for the high-volume intent path.
Don't pay for thinking on "user typed 'coke'".

### Cost shape — order of magnitude, measure before you quote

Rough arithmetic, to show the economics are not the obstacle:

- **Intent parsing:** ~1.5K input + ~200 output on Haiku 5.5 ≈ **$0.25 per
  1,000 queries**, before prompt caching brings it lower. Negligible.
- **Conversational basket:** ~8K input + ~1K output on Opus 5.5 ≈ **$0.05 per
  conversation**. Fine for a feature with a basket-size story.
- **Shelf compliance** is the one with a real bill, because the volume is
  bays × stores × frequency. A shelf photo is roughly 1,500–2,000 input tokens.
  On Haiku 5.5 that is fractions of a penny per bay, and at 600 stores × ~1,000
  bays scanned weekly it lands in the **low tens of thousands per year** —
  tractable. The same workload on Opus 5.5 is **~40× that**, which is not.
  Hence triage on Haiku, escalate only the uncertain bays, and run it through
  the Batch API.

Treat all of these as order-of-magnitude. Measure real token counts with the
token-counting endpoint before putting a number in front of anyone — image
token counts in particular depend on resolution.

---

## Guardrails

### Allergens and dietary claims — the safety-critical one

**Never let a generated response assert that a product is gluten free, nut
free, vegan, or halal.** That claim must come from a structured product
attribute in the catalogue, passed through verbatim. A hallucinated "yes that's
gluten free" is a potential hospital visit and a front-page story.

Concretely: the substitution feature filters candidates on structured dietary
attributes *before* the model sees them, so the model is choosing among
already-safe options rather than judging safety. And the UI shows the attribute
as catalogue data, not as model prose.

This is the one place to be inflexible, and raising it unprompted will do more
for your credibility than any of the features above.

### The rest

- **Grounding:** no location, price or stock figure in a response that didn't
  come from a tool result. Enforce it in review and test for it.
- **Evaluation set:** build a set of real queries with known-correct answers
  before tuning anything. Include the awkward ones — misspellings, ambiguous
  brands, discontinued products, things the store doesn't range. Without this
  you cannot tell whether a prompt change helped.
- **Latency budget:** a shopper standing in an aisle will not wait. Budget the
  whole response, pick the model per path to fit it, and stream so something
  appears immediately.
- **Fallback:** when the model path fails or times out, fall back to plain
  keyword search. The feature degrades; it doesn't disappear.
- **Prompt injection:** product names and descriptions are data in the prompt.
  Treat supplier-supplied catalogue text as untrusted — it is editable by
  parties outside the retailer.
- **Don't log PII into prompts.** Shopper queries can be personal ("medication
  for..."). Decide the retention policy before launch, not after.

---

## Extra questions for the lead — Gen AI specific

These sit alongside the questions in `clarifying-questions.md`.

1. **Is there an approved Gen AI platform?** A retailer this size has model
   governance, a procurement route and an approved-vendor list. We probably
   cannot just call a public API — ask what's already sanctioned.
2. **Data residency.** Does product, store or shopper data have to stay in the
   UK/EU? This constrains which hosting route is usable.
3. **Is customer-facing generated text allowed?** Many retailers permit AI
   internally (colleague tools) long before they permit it in front of
   shoppers. If customer-facing text needs legal/brand sign-off, the colleague
   version ships first — which also happens to be the higher-ROI one.
4. **Shelf photography.** If compliance scanning is interesting, who takes the
   photos — colleagues on handhelds, fixed cameras, or scanning units? And is
   there a policy on cameras capturing shoppers incidentally?
5. **Does an AI/ML team already own some of this?** Product search in
   particular may already be someone's product. Find out before proposing to
   build it.
6. **What is the accuracy bar, and who signs it off?** "The AI must never be
   wrong" is not a bar. Get a measurable one.

---

## Revised phasing

Gen AI slots into the phasing from `solution-sketch.md` without reordering it:

| Phase | Deterministic | Gen AI added |
|---|---|---|
| 0 | Data feasibility spike | Multimodal floor-plan / planogram ingestion to bootstrap the data |
| 1 | Search → availability → aisle | NL query understanding (structured output) + offline catalogue enrichment |
| 2 | Graph + A* routing | NL wayfinding text, pre-generated and cached |
| 3 | QR positioning | — |
| 4 | Shopping list sequencing (TSP) | Conversational basket building |
| 5 | Map visualisation | Voice assistant for colleagues |
| ongoing | — | Shelf compliance triage — arguably should start earlier, since it makes every other phase more accurate |

The ordering principle: **Gen AI makes the data better and the interface
kinder. It does not replace the deterministic core.** Keep search, location,
stock and routing as exact services, and the AI layer stays replaceable, and
testable, and honest.
