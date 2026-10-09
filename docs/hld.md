# High-Level Design

Rendered version with diagrams: **https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB**
Companion architecture note: **https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C**

Both are private — share from each page's Share menu before sending them on.

---

## 1. Consolidated requirements

Every requirement is confirmed, assumed with the assumption recorded, or open.
Nothing is implied.

### Functional

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Search for a product within a given store | confirmed |
| FR-02 | Show availability for the matched product | confirmed |
| FR-03 | Show location — floor, aisle, rack, shelf | confirmed |
| FR-04 | Show the optimal route from the user to the product | confirmed |
| FR-05 | Store spans multiple floors | confirmed |
| FR-06 | Aisles contain multiple racks; rack is addressable | confirmed |
| FR-07 | User position set by manually selecting floor + aisle | confirmed |
| FR-08 | Single product → shortest path | confirmed |
| FR-09 | Multiple products → optimal shopping route | confirmed |
| FR-10 | Fixed floor order, one picking pass per floor | confirmed |
| FR-11 | Multi-product route terminates at a checkout | confirmed |
| FR-12 | **Search bar accepts several products at once**, returning availability for all in one pass, without first building a basket | confirmed |
| FR-16 | **Batch results are grouped by availability, in-stock first**, with a single action that moves only the available items into the basket. An out-of-stock item may be added individually but is flagged not routable | confirmed |
| FR-13 | Basket accumulates items across separate searches, and is the input to routing | confirmed |
| FR-14 | Ambiguous search asks the user to narrow rather than guessing | assumed |
| FR-15 | Out-of-stock items offer in-stock alternatives | assumed |

### Technical and non-functional

| ID | Requirement | Status |
|---|---|---|
| TR-01 | Agentic framework is LangGraph | confirmed |
| TR-02 | Store map authored in-house — no public multi-floor rack-level planogram exists | confirmed |
| TR-03 | Availability data treated as live and correct | confirmed |
| TR-04 | Python · FastAPI · static HTML/SVG frontend · JSON in memory | assumed |
| TR-05 | Search returns in well under a second; no runtime graph search | assumed |
| TR-06 | Model failure degrades to keyword search rather than erroring | assumed |
| TR-07 | No location, stock figure or dietary claim is ever model-generated | confirmed |

### Open — would cause rework

| ID | Question | Impact if answered differently |
|---|---|---|
| OQ-01 | Is the user a shopper or a store colleague? | A colleague picking a 60-item order needs crush-order and temperature constraints and a handheld UI — a different optimisation problem |
| OQ-02 | Source and granularity of real planogram data | Decides whether rack-level addressing exists at all. The long pole |
| OQ-03 | Source of real floor plans, and for how many stores | Per-store digitisation can dwarf the software effort |
| OQ-04 | Approved Gen AI platform, data residency, customer-facing generated text | May force the colleague-facing version first |
| OQ-05 | Accessibility — is step-free routing required? | Second distance matrix over the lift-only subgraph. Cheap if known now |
| OQ-06 | Age-restricted and locked-cabinet products | Needs an "ask a colleague" location type rather than a route |
| OQ-07 | Success metric | Without one the project has no finish line |
| OQ-08 | Multi-store coverage | Store layout becomes a versioned, owned data asset |

### 1.1 What the less obvious requirements actually mean

#### FR-05 · Store spans multiple floors

Not a UI feature. It changes four things:

- **The address.** Floor is part of a location, not metadata about it. "Aisle 7"
  is meaningless alone — there is an Aisle 7 on every floor.
- **The graph is not a flat plane.** Three floor plates, and no edge joins one to
  another except through a vertical connector. You cannot get between floors any
  other way. This is precisely why A* is awkward here: straight-line distance
  assumes you can walk through a ceiling.
- **Routing changes.** A floor transition costs more than its metres — you wait
  for a lift, then ride it — so connectors are weighted edges with a penalty,
  and a multi-product route groups stops by floor rather than treating every
  stop alike.
- **The UI needs one map per floor** with a switcher, and the route drawn across
  plates with transition markers.

For the POC: three floors, one zone per floor, two vertical cores.

#### FR-06 · Racks are addressable

"Addressable" means the rack has its own identifier that the system can store,
look up and route to. It is a real entity in the data model with its own node in
the graph — not a rectangle on a drawing.

| | Not addressable | Addressable |
|---|---|---|
| Planogram says | "Coke is in Aisle 7" | `Coke → F1 · A07 · R03 · S02` |
| Route targets | The aisle entrance | That specific rack |
| Shopper then | Hunts along a 20-metre aisle | Goes straight to it |
| Directions can say | "Aisle 7" | "Two-thirds down on your right, eye level" |

- **Honest distances.** If only aisles were nodes, every product in Aisle 7 would
  sit at the same distance. Rack nodes make the metres real.
- **A stable key.** `F1-A07-R03-S02` identifies a physical slot; the planogram is
  a mapping of SKU onto that address. A range change rewrites the mapping, not
  the map.
- **Shelf position becomes sayable** — eye level, bottom shelf — which is what
  spoken directions need.

#### FR-12, FR-16 and FR-13 · three different things

Routinely confused, and the distinction is where a review will probe:

- **FR-12** — *one* search returns *many* products.
- **FR-16** — one action moves the available ones into the basket.
- **FR-13** — *many* searches contribute to *one* basket, and the basket is what
  gets routed.

FR-12 and FR-13 are orthogonal; both feed the same basket. The basket is not the
mechanism for multi-item search, and saying it is will not survive a follow-up.

#### FR-14 · Ambiguous search asks rather than guessing

"bread" matches forty products with similar scores. Rather than picking one, the
graph pauses on a real `interrupt()` and asks, showing the top options. State is
preserved, so in a batch query only the ambiguous term asks — the others stay
resolved. Capped at two rounds, after which it shows the ranked list and stops
asking.

**Marked assumed for a real reason.** For a shopper, tapping a ranked list may be
better than answering a question; the interrupt earns its place in a
conversational or voice interface. Worth confirming which is wanted.

#### FR-15 · Out-of-stock items offer alternatives

Eggs are out, so instead of a dead end the shopper sees two or three in-stock
alternatives from the same category. The mechanic that matters: candidates are
filtered on structured dietary attributes *before* the model sees them, so it
chooses among already-safe options rather than judging safety. Nothing generated
asserts that a product is gluten free, vegan or nut free — that claim comes from
a catalogue attribute, passed through verbatim.

**Marked assumed because nobody asked for it.** It is the commercial
nice-to-have — a dead end becomes a sale — and the first thing to cut if the week
runs short.

---

## 2. System layers

```
CLIENT          search bar (single · list · natural language) · position picker
                basket · 3 floor plates with route overlay
   │ POST /journey · SSE progress ↩
API             FastAPI, thin: validate · own thread_id · stream · no logic
   │
ORCHESTRATION   LangGraph — 10 nodes, 4 of which call a model
                classify_query · understand_query · resolve_items · clarify
                check_availability · suggest_substitutes · resolve_locations
                route_single · route_multi · describe_route
   │ resolve_items calls ↓
SEARCH          exact match → BM25 lexical → fuzzy fallback
                → structured filter → retail ranking
   │
SERVICES        catalogue · planogram · stock · routing (Dijkstra matrix + TSP)
   │
DATA            products · planogram · stock · store_graph (3 floors, 2 cores)
```

`classify_query` is new since the first architecture draft. It decides the
query's *shape* before anything searches, which is what makes several products
in one search bar work.

---

## 3. Search design

Three separate questions hide inside "how does search work". They have three
different answers.

### 3.1 The matching mechanism

Five stages, tried in order, cheapest first. A query stops at the first stage
that produces confident results.

| Stage | Mechanism | Handles | Implementation |
|---|---|---|---|
| 1 · Exact | Dictionary lookup on barcode or SKU | Scanned EAN-13, internal codes | Python dict, O(1) |
| 2 · Lexical | **BM25** over name + brand + size + category + synonyms | "coke 500ml", "hovis wholemeal" — the overwhelming majority of real queries | `rank_bm25` in memory; OpenSearch BM25 at real scale |
| 3 · Fuzzy | Trigram / Levenshtein, only when BM25 scores come back weak | "paracetomol", "yoghurt" vs "yogurt" | `rapidfuzz`, threshold-gated |
| 4 · Structured filter | Model maps natural language to typed filters that constrain stage 2 | "something gluten free for lunchboxes" | One structured-output call; the model names no product |
| 5 · Ranking | Retail signals re-rank the candidate set | Putting the right Coke first | Deterministic score function |

**Why BM25 and not vector search.** BM25 is a ranked lexical match — it weights
rare terms highly, dampens repeated ones, and normalises for field length, which
suits short product names. It is also explainable: you can say why a result
ranked where it did, which matters when a buyer asks why their product is not
showing.

Vector search is deliberately *not* in the design. At 200 SKUs the semantic
cases are handled better by stage 4 — the model maps intent to a category and
dietary filter, and BM25 searches within it. Cheaper, explainable, and unable to
return a product that does not exist. Vector search earns its place at a
50,000-SKU catalogue where an LLM call per query is too slow; the pattern there
is hybrid BM25 + embeddings fused with reciprocal rank fusion. Name it as the
scale-up path, don't build it now.

**Ranking signals, in priority order:**

1. Ranged in this store — a product this branch does not carry never outranks one it does
2. In stock — available beats unavailable
3. BM25 relevance
4. Exact size or variant match when the query names one ("500ml")
5. Own-brand and popularity as a tiebreak

### 3.2 Several products in one search

Yes — and **not via the basket**. The basket accumulates items across *separate*
searches; it is not the mechanism for putting several products into one search.
That is a batch query, handled by `classify_query` before any searching happens.

| Input | Classified as | Behaviour |
|---|---|---|
| `coke 500ml` | single term | One product, availability, location, route |
| `milk, bread, eggs` | delimited list | Three rows, each with its own availability and location, plus one combined route offered |
| `milk and 6 eggs and some bread` | delimited list | Same. `" and "` is a delimiter; quantities are parsed off the term |
| `what do I need for a fry up` | natural language | Model expands to an item list, then the batch path. Items shown for confirmation before routing, because the model chose them |
| `5010029000061` | barcode | Exact lookup, single product |

Classification order: empty/too-short → reject · all-digits → barcode ·
contains `,` `;` newline or `" and "` → split · >4 words with verbs → model ·
otherwise → BM25. A batch query runs the whole tree once per term,
concurrently.

### 3.3 Checking availability for all of them at once

This is the part a basket answer misses, and it is a separate design point from
batch search. Resolving several terms gives several SKUs; the availability check
on them must be **one call, not N**.

`check_availability` takes a *list* of SKUs and returns a map. At POC scale that
is a dict comprehension; against a real stock service it is the difference
between one request and sixty. Designing the signature as a batch from the start
costs nothing now and avoids an N+1 rewrite later. Same for
`resolve_locations`.

So: availability for several products up front, in a single pass, and the route
is then *offered* rather than forced — the shopper sees what is in stock and
where before deciding whether to walk it.

### 3.4 Batch results and the basket gate

Resolving several terms produces a mixed result — some in stock, some not.
Routing straight off that set is wrong, because it would plan a walk to shelves
with nothing on them. So a basket gate sits between search and routing:
**results are grouped with the available items first, and one action moves only
those into the basket.**

```
batch search  →  results grouped: AVAILABLE first, out of stock below
              →  [Add 3 available to basket]      ← one action
              →  basket holds only routable items
              →  [Plan route]
```

The basket is then the input to routing, so a route is never computed for
something that is not there. It also disposes of the all-out-of-stock case
without special handling — the action is simply disabled.

An out-of-stock item **can** be added individually, for a shopper who intends to
ask a colleague, but it is flagged not routable and excluded from the path, with
the exclusion stated rather than silent.

Consequence for the sequence: the first journey call returns **results only**.
Routing is a second call, made from the basket.

---

## 4. Edge cases

### 4.1 Search

| ID | Scenario | Behaviour |
|---|---|---|
| EC-01 | Empty or one-character query | Reject before any search; show category browse |
| EC-02 | Misspelling — "paracetomol" | Weak BM25 scores → fuzzy stage → retry once only, to bound latency |
| EC-03 | No match anywhere in the catalogue | "We don't recognise that" + nearest fuzzy suggestions. Never an empty screen |
| EC-04 | In the catalogue but not ranged in this store | Say so explicitly, offer the nearest ranged alternative. Early graph exit, no route |
| EC-05 | Ambiguous — "bread" returns 12 near-equal hits | `clarify` interrupt with the top options. Capped at two rounds, then show the ranked list |
| EC-06 | Batch query with 200 pasted terms | Cap at 30 resolved items; return the rest unprocessed with a clear message |
| EC-07 | Duplicate terms — "milk, milk, bread" | Deduplicate *after* resolution — "milk" and "whole milk" may resolve to the same SKU |
| EC-08 | One term in a batch resolves to nothing | Partial success. Return what resolved, name what didn't. Never fail the whole query |
| EC-09 | Query is a category, not a product — "dairy" | Show the aisle and offer to browse rather than returning an arbitrary SKU |
| EC-10 | Unknown barcode scanned | Distinguish "not a valid EAN" from "valid but not in our catalogue" |
| EC-11 | Prompt injection in the query or in supplier-supplied product text | Query text passed as data, never concatenated into instructions. Catalogue descriptions treated as untrusted — editable outside the retailer |
| EC-12 | Medical or dosage question | Out of scope by design. Locate the pharmacy aisle; give no medical advice |

### 4.2 Availability

| ID | Scenario | Behaviour |
|---|---|---|
| EC-13 | Out of stock | Still show the location — "usually Aisle 7, currently out" — and offer substitutes |
| EC-14 | Stock changes between search and routing | Re-check at route time; drop the item and say which one and why |
| EC-15 | Every item in a batch out of stock | The "add available" action is disabled and nothing enters the basket, so there is no route to refuse. Substitutes offered for each |
| EC-16 | Some available, some not | The designed case, not an exception. Available group first, one action moves those to the basket, the rest listed with substitutes |
| EC-46 | Shopper adds an out-of-stock item individually | Allowed — they may intend to ask a colleague — but flagged not routable and excluded from the path, with the exclusion stated rather than silent |
| EC-17 | Product delisted mid-session | Basket entries revalidated on every journey call, never trusted from session state |
| EC-18 | Stock service unreachable *(real build)* | Degrade to location-only with availability marked unknown. Never render a guess as a fact |

### 4.3 Location and planogram

| ID | Scenario | Behaviour |
|---|---|---|
| EC-19 | SKU has no planogram entry | Show availability, state the location is unknown rather than inventing one |
| EC-20 | SKU has several locations | Show all; route to the nearest. The normal case, not an exception |
| EC-21 | Planogram references an aisle absent from the store graph | Data integrity failure, caught by startup validation, not at request time |
| EC-22 | Locked cabinet — spirits, formula, razor blades | Location type `ASSISTED`: route to the cabinet, state a colleague must unlock it (OQ-06) |
| EC-23 | Behind a counter — deli, pharmacy, fish | Location type `COUNTER`: route to the counter, no rack or shelf |
| EC-24 | Seasonal bay currently empty | Flagged seasonal; suppressed at zero stock so shoppers aren't sent to bare shelving |

### 4.4 Routing

| ID | Scenario | Behaviour |
|---|---|---|
| EC-25 | Shopper already in the product's aisle | Zero-length route. "You're in the right aisle — rack 3, eye level". Draw no line |
| EC-26 | All items on one floor | No vertical transition; floor clustering collapses to a single pass |
| EC-27 | Items across all three floors | Highest floor first, work down, finish at the tills |
| EC-28 | Single item submitted in multi mode | Falls through to the single-product path; TSP not invoked for one stop |
| EC-29 | Unreachable node — orphaned aisle | scipy writes `-9999` to predecessors and `inf` to distances. Both checked; startup validation rejects a disconnected graph |
| EC-30 | Lift out of service | Remove the edge and recompute the matrix — sub-second, so it can run on demand. The other core absorbs the traffic |
| EC-31 | Step-free requested but none exists | Say so plainly rather than silently returning a route with stairs |
| EC-32 | Route would pass through a closed zone | Zones carry an open flag; closed-zone edges filtered before the matrix is built |
| EC-33 | Chilled and frozen in a multi-item route | Deferred to the final floor pass — a natural consequence of ending at the tills |

### 4.5 Orchestration

| ID | Scenario | Behaviour |
|---|---|---|
| EC-34 | Clarification abandoned, interrupt never resumed | Threads carry a TTL and are swept. Without this every abandoned search leaks a checkpoint — LangGraph does not expire threads on its own |
| EC-35 | Clarify loop never converges | Loop counter in state, capped at two rounds, then forced to return the ranked list |
| EC-36 | Same `thread_id` from two tabs at once | Last write wins; the UI reloads graph state rather than trusting local state |
| EC-37 | Model call times out or errors | Every model node has a deterministic fallback: keyword search, a static substitution table, a directions template. The journey always completes |
| EC-38 | Model returns malformed structured output | Validate against the schema; fall back to keyword search. Known interaction with thinking enabled |
| EC-39 | Model declines the request | Check the stop reason before reading content; fall through to the deterministic path |
| EC-40 | Node raises mid-graph, partial state | The checkpoint holds the last good state; resume from the failed node rather than restarting |
| EC-41 | SSE stream drops mid-journey | Result retrievable by `thread_id` — progress streaming is a convenience, not the delivery mechanism |

### 4.6 Data and startup

| ID | Scenario | Behaviour |
|---|---|---|
| EC-42 | Malformed store graph | Fail at startup with a clear error. Never serve a half-loaded graph |
| EC-43 | Planogram references SKUs absent from the catalogue | Startup validation lists the orphans and refuses to start |
| EC-44 | Disconnected graph components | Connectivity check at startup. A store you cannot walk across is a data bug, not a routing edge case |
| EC-45 | Zero or negative edge weight | Rejected at load. Negative weights break Dijkstra's correctness guarantee outright |

---

## 5. Likely review questions

**What search mechanism is it?** BM25 lexical ranking over a normalised product
text field, with exact barcode lookup in front and fuzzy matching behind it for
typos. Natural-language queries go through the model first, which produces a
typed filter constraining the same BM25 search — the model narrows the search,
it never names the product.

**Why not vector search?** At this catalogue size the model's structured filter
handles the semantic cases more cheaply and more explainably, and it cannot
return a product that does not exist. Hybrid BM25 + embeddings with reciprocal
rank fusion is right at tens of thousands of SKUs. Scale-up path, not starting
point.

**If I type several products into the search bar, does it work?** Yes.
`classify_query` detects the delimiters and splits the input; each term resolves
independently and concurrently. The basket is for accumulating across separate
searches — it is not the mechanism for multi-item search.

**Can I see availability for all of them up front?** Yes, in one batched call
rather than one per item. The route is then offered, not forced.

**What happens when the search is ambiguous?** The graph pauses on a real
interrupt and asks, keeping the terms already resolved. Capped at two rounds.

**What algorithm computes the route?** Dijkstra from every node once at startup,
giving a distance matrix and a predecessor matrix, so every single-product query
is an O(1) lookup. A* is the wrong tool: it optimises one query at a time, and
across floors straight-line distance is not admissible because a route cannot
pass through a ceiling.

**What if the model is wrong or unavailable?** Every model node has a
deterministic fallback, and no model sits on the path returning a location, a
distance or a stock figure. The system degrades to keyword search — less fluent,
never wrong about where something is.

**Is this ready for a real store?** No, and not meant to be. The journey, the
interface and the data model are proven on synthetic data. What stands between
this and a real store is data, not software.

**Is this a machine learning problem?** No. It is search and graph routing over
enumerable data. BM25 is statistical ranking, not learned; Dijkstra and the
2-opt heuristic are classical algorithms with exact or provable answers. The
only learned component is a pre-trained model called for language understanding
— inference, not training. There is no dataset, no labels, no model to fit and
no training pipeline.

**Shouldn't we train a model on the store data so it learns the map?** No, and
this is the most common misconception about this kind of system. **The store map
is not a pattern to learn, it is a fact to look up.** Training is for rules you
cannot enumerate; this map is 300 nodes and 900 edges in a file. Training a
model to hold it is like training one to remember a phone number instead of
writing it down.

| | Trained model | Lookup + Dijkstra |
|---|---|---|
| Accuracy | Approximates distances, sometimes wrong | Exact, provably shortest |
| Shelf moves at a range change | Retrain | Edit one row |
| 600 stores | 600 models | 600 files |
| "Why this route?" | No answer available | Trace the path |
| Cost per query | Inference | An array read |

The failure mode is the real objection: a model that has "learned" the map will
confidently invent an aisle number for a product it did not memorise — exactly
what this architecture exists to prevent.

**What the model is for is language, not geography.** It turns "something gluten
free for the kids' lunchboxes" into a structured query and hands that to BM25,
which searches the real catalogue. It never knows where anything is, and its
output schema carries no field for a product name or a location (LLD §9), so it
cannot.

Google Maps does not train a model to learn the road network — it stores roads
as a graph and runs a routing algorithm. Its machine learning is for traffic
prediction and for understanding "coffee near me", not for knowing where streets
are. The same split applies here.

Training would be the right call with click logs and a learning-to-rank goal, or
shelf photos and a compliance-detection goal. Neither is this project.

---

## 6. Where this design is weakest

Say these before someone finds them.

**A planogram says where a product is *supposed* to be.** Shelves drift from
plan within days of a range change. Synthetic data hides this completely, so the
demo will look more reliable than a real deployment would. Honest mitigations
are a user "this is wrong" report and, longer term, vision-based shelf
compliance.

**The open questions in section 1 are genuinely open.** If the user turns out to
be a colleague picking online orders rather than a shopper, the optimisation
problem changes shape.
