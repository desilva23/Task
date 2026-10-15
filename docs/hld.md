# High-Level Design

Rendered version with diagrams: **https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB**
Companion architecture note: **https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C**

Both are private — share from each page's Share menu before sending them on.

---

## 1. What this document owns

The requirements live in `requirements.md` — 24 functional, 11 non-functional
and 27 acceptance criteria, every one confirmed. They are not repeated here.
This document owns the component architecture, the search design, the interface
and the edge cases, and it is written to be read after the specification.

Three constraints shape everything below: **LangGraph** orchestrates the
pipeline (C-01), the implementation is **Python** (C-02), and the interface is a
single **Next.js** page calling the compiled graph through a small **HTTP API**
(C-03), both deployed on Vercel (C-07). The API is **stateless**: nothing about a
shopper survives between two requests on the server (§4.1).

### 1.1 What the harder requirements mean for the design

#### Multiple floors — FR-10, FR-14 and A-03

No single requirement says "the store has floors": A-03 fixes the demo store at
three, FR-10 makes floor part of every location, and FR-14 lets a route cross
them. Together they change four things:

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

#### FR-10 · Racks are addressable

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

#### FR-02, FR-21 and FR-23 · three different things

Routinely confused, and the distinction is where a review will probe:

- **FR-02** — *one* search returns *many* products.
- **FR-21 and FR-22** — results are grouped by availability, and one action
  moves only the available ones into the basket.
- **FR-23** — *many* searches contribute to *one* basket, and the basket is what
  gets routed.

FR-02 and FR-23 are orthogonal; both feed the same basket. The basket is not the
mechanism for multi-item search, and saying it is will not survive a follow-up.

#### FR-05 · Ambiguous search asks rather than guessing

"bread" matches forty products with similar scores. Rather than picking one, the
graph pauses on a real `interrupt()` and asks, showing the top options. State is
preserved, so in a batch query only the ambiguous term asks — the others stay
resolved. Capped at two rounds, after which it shows the ranked list and stops
asking.

**Confirmed, and AC-03 tests the part that matters**: the chosen option must
resolve without the shopper re-entering the other terms. A clarification that
loses the rest of the search is worse than a ranked list.

#### FR-09 · Out-of-stock items offer alternatives

Eggs are out, so instead of a dead end the shopper sees two or three in-stock
alternatives from the same category. The mechanic that matters: candidates are
filtered on structured dietary attributes *before* the model sees them, so it
chooses among already-safe options rather than judging safety. Nothing generated
asserts that a product is gluten free, vegan or nut free — that claim comes from
a catalogue attribute, passed through verbatim.

**Confirmed, and AC-17 is deliberately strict**: every candidate offered must
itself be in stock and compatible with the original's recorded dietary
attributes, and where no compatible alternative exists the system says so rather
than offering an incompatible one. A substitute is the one place a shopper could
be handed something their diet excludes, which is why the filter runs before the
model rather than after it.

---

## 2. System layers

```
PAGE            Next.js, one static page: search form · barcode scan · position
                picker · basket · floor plates with route overlay · directions list
   │ HTTPS, JSON: /api/store · /api/search · /api/scan · /api/route
API             FastAPI, one Python function — stateless; each request is one or
                more graph runs on a fresh thread, deleted before it returns
ORCHESTRATION   LangGraph — 11 nodes, 3 of which call a model
                classify_query · understand_query · resolve_items · clarify
                check_availability · suggest_substitutes · resolve_locations
                route_single · route_multi · describe_route · verify
   │ nothing reaches the page until verify has passed it ↑
   │ resolve_items calls ↓
SEARCH          exact match → BM25 lexical → fuzzy fallback
                → structured filter → retail ranking
   │
SERVICES        catalogue · planogram · stock · routing (Dijkstra matrix + TSP)
   │
DATA            products · planogram · stock · map_nodes · map_edges
                CSV, cached once (3 floors, 2 vertical cores)
```

`classify_query` decides the query's *shape* before anything searches, which is
what makes several products in one search bar work. It is a pure function: a
regex over delimiters and word count, with no model call.

### 2.1 Agent decomposition

Eleven nodes on **explicit edges**, grouped by the job they do. Read as agents,
they are six:

| Role | Nodes | Model |
|---|---|---|
| Query understanding | `classify_query` · `understand_query` · `resolve_items` · `clarify` | `understand_query` only — it produces a typed filter, never a product name |
| Availability | `check_availability` · `suggest_substitutes` | `suggest_substitutes` only, over a candidate set already filtered for stock and diet |
| Location | `resolve_locations` | None |
| Routing | `route_single` · `route_multi` | None |
| Narration | `describe_route` | Phrasing only, over facts it is handed |
| Verification | `verify` | None — it is the check on everything above it |

Three nodes call a model; eight are plain functions. Every node that decides
*where a shopper walks* — location and both routing nodes — sits in the
model-free half, which is NFR-01 expressed as a graph rather than as a
promise. Each model node has a named deterministic
fallback — keyword search, a static substitution table, a directions template
(EC-37) — so NFR-04 holds and AC-11 can prove it.

**Why explicit edges rather than a tool-calling agent.** The sequence is known:
availability is always checked before a route is planned, because a route to an
empty shelf is worse than no route at all. An agent that re-decides the order on
every query can get that wrong, and buys nothing in exchange. The fixed order is
a safety property, not a missing feature.

What makes this agentic is the rest of the machinery: shared typed state, a
checkpointer, the `clarify` cycle with its own termination counter, and a real
`interrupt()` that suspends a journey mid-flight and resumes it with the already
resolved terms intact. Those are the parts a plain script cannot do.

#### `verify` — the last gate

The final node before the page. It takes the composed answer and re-checks
every factual claim in it against the service results that produced them:
each SKU, floor, aisle, rack and shelf, each availability statement, the route
distance, and the floor transitions named in the directions.

A claim that does not match is **not corrected and shown — it is never shown**.
The node discards the composed text and re-renders from the deterministic
template, exactly as it would if the model had been unavailable, and records
the discrepancy in `degraded`.

Two reasons it is a node and not a helper function. It must be impossible to
reach the page without passing through it, which an edge guarantees and a
convention does not. And it is the component that makes NFR-02 a thing the
system *does* rather than a property it is claimed to have — AC-10 feeds in a
deliberately corrupted claim and asserts it never reaches the shopper.

Grounding is enforced twice over, and the two are not redundant: the types stop
the model naming a product or a location at all (LLD §9), and `verify` catches
everything downstream of that — a stale cached figure, a mis-joined placement,
a template that formatted the wrong leg. One prevents invention, the other
catches error.

### 2.2 How one request flows

A shopper standing in the Bakery on Floor 1 types
`milk, bread, crayons, batteries`. The layer stack says what exists; this says
what happens.

```
SHOPPER    PAGE        API · GRAPH              SERVICES        CSV
   │ types  │            │                         │             │
   1───────▶│            │                         │             │
   │        2───────────▶│  POST /api/search       │             │
   │        │            3  classify_query         │             │
   │        │            │  → batch, 4 terms       │             │
   │        │            4  resolve_items ────────▶5 catalogue──▶6
   │        │            │  ◀── ranked candidates per term       │
   │        │            7  one term ambiguous → interrupt()     │
   │   ◀────8  "bread: sourdough / white / wholemeal?"           │
   9───────▶│  taps one  │                         │             │
   │        10──────────▶│  POST /api/search + the answer: the   │
   │        │            │  run is repeated and resumed with it  │
   │        │            11 check_availability ───▶12 stock ────▶│
   │        │            │  → 3 in stock · crayons out of stock  │
   │        │            13 suggest_substitutes ──▶ candidates   │
   │        │            14 resolve_locations ────▶15 planogram─▶│
   │   ◀────16 results grouped: 3 available, 1 out + alternatives│
   17──────▶│  "add 3 available to basket" → "plan route"        │
   │        18──────────▶│  POST /api/route — the basket's SKUs  │
   │        │            19 route_multi ──────────▶20 routing    │
   │        │            │  floors clustered, 2-opt per floor    │
   │        │            21 describe_route (model phrases it)    │
   │        │            22 verify — every claim re-checked      │
   │   ◀────23 directions + route drawn on each floor plate      │
```

Three things in that sequence are the design, not decoration. The interrupt at
step 7 keeps the other three terms resolved, so a clarification costs one tap
and not a retyped search — the page sends the search back with the answer and
the server, which kept nothing, repeats the run and resumes it (§4.1). The basket gate at step 17 is why no route is ever
planned to the empty crayon shelf. And step 22 stands between every answer and
the shopper.

Nothing below the graph row ever talks to a model, and nothing above the
services row ever reads a CSV.

#### What the shopper gets

```
Semi-skimmed milk 2 L        Available      F1 · Aisle 3 · Rack 2 · shelf 2
Sourdough loaf 800 g         Available      F1 · Aisle 1 · Rack 4 · shelf 3
AA batteries 8 pack          Available      F2 · Aisle 14 · Rack 1 · shelf 1
Crayola crayons 24 pack      Out of stock   F2 · Aisle 11 · Rack 1
                             → in stock instead: Crayola 12 pack,
                               Staedtler 24 pack

Route from Bakery, Floor 1 — 112 m, 3 stops, one trip upstairs
  1. Take the north stairs or the lift up to Floor 2
  2. Aisle 14, rack 1, bottom shelf — AA batteries
  3. Back down to Floor 1, head for Aisle 1
  4. Rack 4 on your right, shelf 3 — sourdough
  5. Continue to Aisle 3, rack 2 at eye level — milk
  6. Checkouts are ahead of you

Crayons are out of stock and left out of the route.
```

Read the route order against FR-17 and FR-18: the upper floor is cleared first
and the trip finishes at the tills, so the shopper never climbs twice and the
chilled milk is picked last. A distance-only optimiser would have sent them up
and down.

Distances are illustrative — the demo store is synthetic (C-04).

---

## 3. Search design

Three separate questions hide inside "how does search work". They have three
different answers.

### 3.1 The matching mechanism

Five stages, tried in order, cheapest first. A query stops at the first stage
that produces confident results.

| Stage | Mechanism | Handles | Implementation |
|---|---|---|---|
| 1 · Exact | Dictionary lookup on the normalised name and known synonyms | "semi skimmed milk", "kitchen roll" typed as the catalogue spells them | Python dict, O(1) |
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

Classification order: empty/too-short → reject · digits only → not a product
request · contains `,` `;` newline or `" and "` → split · >4 words with verbs →
model · otherwise → BM25. Digits typed into the search box are not searched (EC-10):
a barcode is looked up through the scan (§3.5), where an exact match is the only
answer. A batch query runs the whole tree once per term, concurrently.

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

Consequence for the sequence: the first graph run returns **results only**.
Routing is a second request, `/api/route`, sent from the basket the page holds;
availability is read afresh then, so the route cannot reach an empty shelf.

---

### 3.5 Barcode scan

FR-03 earns its place in two cases typed entry does not serve: working from an
empty packet brought from home, and checking you have the right variant of
something you are holding. Typed digits are the degraded path, for when the
camera is declined, missing or cannot start (A-07, C-08).

**Decoded live, in the browser.** The page reads frames from the camera and
decodes them on the phone, with the same zxing decoder compiled to WebAssembly;
the shopper holds the barcode up and no shutter is tapped. Only the digits are
sent to the server — **no image ever leaves the phone**, so there is nothing to
store, log or pass to a model. The camera stops as soon as a code is read.

**A barcode is an identifier, not a search.** The decoded or typed digits are
checked — length and GS1 check digit — and then looked up for an exact match in
the catalogue. There is no ranking, no fuzzy retry and no nearest match: a
barcode that is not in the catalogue says so (AC-28), because the nearest
product to a wrong number is a wrong product. Only retail symbologies (EAN-13,
EAN-8, UPC-A) are read; a QR code or a shipping label is not a product. The
server checks the digits again whatever the page sent: the page is not trusted
to have decoded honestly.

**The same graph, entered at the same door.** A scan is a request with
`action = scan`. `classify_query` checks the digits; a valid code goes straight
to `resolve_items`, skipping the model, and from there the journey is the one a
typed single product takes — availability, substitutes, location, route,
narration and `verify`. No node is added, and the scanned product reaches the
basket by the same button. The synthetic catalogue's barcodes sit in the GS1
`20`–`29` range, reserved for in-store numbering, so no real product's barcode
can match one by accident.

### 3.6 Stock alerts

The store manager gets two emails, through AgentMail (C-09): **low stock** when a
stocked product's shelf quantity falls to `LOW_STOCK_UNITS` or below, and **out of
stock** when it reaches zero (FR-26). Each lists every product that crossed into
that state in this update, with the units left and where it sits — floor, aisle,
rack and shelf — so the manager knows which shelf to deal with.

**Alerts are changes, not states.** Stock arrives as a new version of the store's
stock file (A-08). The alert job compares that version with the one before it and
reports a product only when it got worse: fine → low, fine → out, low → out. A
product that stays low, recovers, or is not stocked at this branch sends nothing,
so the manager is never told the same thing twice and no record of past alerts is
needed. When alerts are first switched on, one "current state" email lists
everything already low or out.

**Plain code end to end.** Which products crossed, and every word of the email,
come from the stock data and the planogram; no model is involved, so there is
nothing to verify. The job runs in GitHub Actions on each push to `main` that
changes a `stock.csv`, with the AgentMail key, the sending inbox and the manager's
address held as repository secrets — the repository is public, and none of the
three is in it. Each email carries an idempotency key built from the store, the
commit and the alert kind, so re-running the job never delivers an email twice.

### 3.7 Voice input

FR-27 is for a shopper with their hands full — a basket on one arm, a child by
the other — or who would rather say a product than spell it. It is a way of
typing, not a new kind of search.

**The browser turns speech into words.** The page uses the browser's own speech
recogniser (the Web Speech API), set to British English, behind a microphone
button in the search box. Nothing is asked for until the button is tapped; it
listens for one request, shows the words in the box as they are recognised, and
when the shopper stops, runs the search on them. Only the words reach this
system's server — **no audio is sent to it or stored by it** — and from there the
request is a typed one: the same call, the same graph, the same ranking and the
same clarifying question. The model is not asked to transcribe or interpret
sound, so voice adds no model call and no new way for a fact to be invented.

**What the browser does with the sound is the browser's.** Chrome sends it to
Google's speech service; Safari uses Apple's, on the phone or on Apple's servers (A-09). That is the cost of a free
recogniser with nothing to host; the alternative — audio to our own function and
a speech model there — would put shoppers' voices on our side of the line.

**The words stay in the box.** A misheard word is not a dead end: it is in the
search box, where it can be corrected by typing and searched again, and a search
that matches nothing says so the way a typed one does (EC-64). Where the browser
has no recogniser the button is not drawn at all (EC-62).

## 4. Interface and presentation

One Next.js page, used by a shopper standing in the store on their own phone
(A-06). The page is not a thin shell over the graph — six requirements land
here and nowhere else.

**One screen, three panes.** The page never scrolls (NFR-11). A header carries where the
shopper is — "Floor 0 · Entrance", tapped to change it in a sheet — and a tab bar at the bottom
switches between **Search**, **Basket** and **Route**, each of which fits the space between.
Search holds the box, its suggestions, the microphone, "Scan a barcode" (a sheet with the
camera) and the results as short cards, available first, with the basket action under them.
Basket lists what is collected and plans the route. Route shows the floor plate in its own
frame, opened on the step's shelf and dragged like any map, with the directions under it one
step at a time, each step showing its own floor; "All steps" swaps the map for the whole list.
Only a long list or the map moves, inside its own frame.

| Requirement | What the page does |
|---|---|
| FR-03 · barcode scan | A "Scan a barcode" button beside Search opens a sheet with the camera. Only then does the camera start, so no permission is asked until the shopper wants it; frames are decoded as they arrive, and beneath the camera a field for the digits does the same lookup. A read closes the sheet and shows the product |
| FR-28 · suggestions | From two letters, a list under the box of up to six products this store sells whose words begin with what was typed — those whose name or a synonym starts with it first, then in stock, then the popular; a sold-out one says so. Arrow keys and Enter, or a tap, choose one; its name and size replace the item being typed and the search runs. The catalogue comes once with the store call and is matched on the phone, so a keystroke reaches no server and no model, and a product's label searches straight to it, so the suggestion and the answer cannot disagree |
| FR-27 · voice | A microphone button at the end of the search box, drawn only where the browser can recognise speech. One tap listens for one request; the button turns red while it records, the words fill the box as they are heard, "Listening…" says it is on, and when the shopper stops the search runs. A second tap stops the recording at once and searches what was heard so far |
| FR-15 · start point | In a sheet from the header: two selects, floor then aisle, defaulting to the entrance. No positioning technology is used or implied; the start point is self-reported |
| FR-20 · route presented twice | Step-by-step directions as text, and the same route drawn over one SVG floor plate per floor. The plate is read without explanation: turned upright for a phone (front of store on the right), every aisle labelled with its number and what it sells, counters and locked cabinets named on the rear wall, both stairs-and-lift cores, the checkouts and the entrance named, "Start here" and "Pay here", each pick a numbered pin on its shelf, named with its aisle, rack and shelf in a list under the plan, and each floor change written out — which way, by stairs or lift, to which floor. No label may touch a shelf, box, pin or another label, or run off the plate |
| NFR-10 · screen reader | The directions list *is* the accessible route, not a caption on a drawing: ordered text, one instruction per step, naming floor, aisle, rack and shelf position. The map is never the only way to read the route |
| NFR-11 · phone width | One screen at 390 × 844: header, one pane, tab bar, and the page never scrolls. The floor plate keeps its readable size in a frame of its own, and the primary buttons sit at the bottom, within thumb reach |

**Explainability is a presentation requirement too** (NFR-09). The page can
always answer two questions, and both answers come from the mechanism itself.

*Why is this product third?* Because it is out of stock, and in-stock items
rank above out-of-stock ones. Ranking is a list of rules in priority order, so
the reason is whichever rule pushed it down.

*Why did the route go this way?* Entrance → Aisle 1 → Aisle 3 → checkout. The
route **is** an ordered list of points, so printing that list is the
explanation.

A model could be asked either question and would answer fluently. But it never
saw the ranking rules or the path — it would be inventing a reason that sounds
right, not reporting the real one. An explanation nobody can check is worse
than none, because it gets believed.

### 4.1 Mechanics of a stateless API

The agent runs as a serverless function: any request may reach a fresh
instance, and two requests from one shopper may reach different ones. Four
consequences are design-level rather than implementation detail:

1. **The expensive objects are built once per instance**, when the function
   starts: store, BM25 index, and the distance and predecessor matrices. Every
   request on a warm instance reuses them; only a cold start pays for them,
   and NFR-05 is measured warm and cold.
2. **The search commits on submit**, so the agent runs once per search rather
   than once per keystroke. Suggestions as the shopper types (FR-28) need no request at all:
   the store call carries the catalogue's labels, and the phone matches them.
3. **The clarification is carried by the page, not the server.** FR-05's
   `interrupt()` still suspends the graph, but the request that asked the
   question has ended by the time the shopper answers. The page sends the
   search back with the answers; the server runs the graph again on a fresh
   thread and resumes it with each round's answer in turn. Only an option the
   graph itself offered is accepted (EC-05), and a thread is deleted before its
   request returns, so an abandoned question leaves nothing behind (EC-34).
4. **The basket and the shopper's position live in the page**, and a route is
   planned from the SKUs the page sends. Availability and routability are
   re-read from the store data on every request, so a stale page can ask for a
   route but never receive one to an empty shelf (EC-17).

The model-call budget per visitor (constitution: public-deployment guard) is
counted in a cookie, because there is no server-side session. A visitor who
clears cookies resets it, so it is a courtesy limit; the binding limits are the
spend cap in the Groq console and a rate limit at Vercel's firewall.

---

## 5. Quality goals

The non-functional requirements and the design that meets each. Every row names
the acceptance criterion that tests it, so none of this rests on assertion.

| Goal | How the design meets it | Tested by |
|---|---|---|
| **Correct answers** (NFR-01) | Locations, stock and distances come only from the services. The model's output schema has no field for a product name or a location, so it cannot supply one | AC-10 |
| **Verified before display** (NFR-02) | `verify` is the last node; a claim that does not match the service result is discarded and the deterministic template is rendered instead | AC-10 |
| **Dietary safety** (NFR-03) | Substitute candidates are filtered on recorded attributes *before* the model sees them. A `null` attribute reads as unknown and excludes the candidate | AC-17 |
| **Reliability** (NFR-04) | Each of the three model nodes has a named deterministic fallback; `degraded` records which fired. No model sits on the path that returns a location or a distance | AC-11 |
| **Speed** (NFR-05) | All-pairs shortest paths are precomputed at startup, so routing is a matrix lookup. BM25 index and distance matrices are built once per function instance and reused by every request on it | AC-12 |
| **Input safety** (NFR-06) | Shopper text is passed as data, never concatenated into instructions. Tool arguments are typed and validated. Catalogue text is treated as untrusted — it is editable outside the retailer | AC-13 |
| **Data integrity** (NFR-07) | The store folder is validated at load: orphan SKUs, placements pointing at missing map points, disconnected components and non-positive edge weights all refuse startup | AC-14 |
| **Portability** (NFR-08) | Nothing store-specific exists above the data layer. A second store with a different floor count is a replaced set of data files | AC-09 |
| **Explainability** (NFR-09) | Ranking is a lexicographic tuple sort, so the order can be stated as a reason rather than a score. A route can be read back as the node path it came from | — |
| **Accessibility** (NFR-10) | Step-free routing runs over a second distance matrix built on the lift-only subgraph. The directions list is the accessible route, not a caption on the map | AC-07 |
| **Mobile** (NFR-11) | Single column at 390 px, floor plate scaled to width, no horizontal scroll | AC-15 |

---

## 6. Edge cases

### 6.1 Search

| ID | Scenario | Behaviour |
|---|---|---|
| EC-01 | Empty or one-character query | Reject before any search; show category browse |
| EC-02 | Misspelling — "paracetomol" | Weak BM25 scores → fuzzy stage → retry once only, to bound latency |
| EC-03 | No match anywhere in the catalogue, or a match on only part of the search — "face wash" against Shower Gel ("body wash") | "We don't recognise that" + suggestions: products named by more of the words first, then by the last word, then the popular. A product named by part of a search is never the answer. Never an empty screen |
| EC-04 | In the catalogue but not ranged in this store | Say so explicitly, offer the nearest ranged alternative. Early graph exit, no route |
| EC-05 | Ambiguous — "bread" returns 12 near-equal hits | `clarify` interrupt with the top options. Capped at two rounds, then show the ranked list |
| EC-06 | Batch query with 200 pasted terms | Cap at 30 resolved items; return the rest unprocessed with a clear message |
| EC-07 | Duplicate terms — "milk, milk, bread" | Deduplicate *after* resolution — "milk" and "whole milk" may resolve to the same SKU |
| EC-08 | One term in a batch resolves to nothing | Partial success. Return what resolved, name what didn't. Never fail the whole query |
| EC-09 | Query is a category, not a product — "dairy" | Show the aisle and offer to browse rather than returning an arbitrary SKU |
| EC-10 | Query is digits only | Treated as not a product request rather than searched, and the shopper is pointed to the barcode scan (§3.5), where digits are an exact lookup |
| EC-11 | Prompt injection in the query or in supplier-supplied product text | Query text passed as data, never concatenated into instructions. Catalogue descriptions treated as untrusted — editable outside the retailer |
| EC-12 | Medical or dosage question | Out of scope by design. Locate the pharmacy aisle; give no medical advice |

### 6.2 Availability

| ID | Scenario | Behaviour |
|---|---|---|
| EC-13 | Out of stock | Still show the location — "usually Aisle 7, currently out" — and offer substitutes |
| EC-14 | Stock changes between search and routing | Re-check at route time; drop the item and say which one and why |
| EC-15 | Every item in a batch out of stock | The "add available" action is disabled and nothing enters the basket, so there is no route to refuse. Substitutes offered for each |
| EC-16 | Some available, some not | The designed case, not an exception. Available group first, one action moves those to the basket, the rest listed with substitutes |
| EC-46 | Shopper adds an out-of-stock item individually | Allowed — they may intend to ask a colleague — but flagged not routable and excluded from the path, with the exclusion stated rather than silent |
| EC-17 | Product delisted mid-session | Basket entries revalidated on every journey call, never trusted from session state |
| EC-18 | Stock service unreachable *(real build)* | Degrade to location-only with availability marked unknown. Never render a guess as a fact |

### 6.3 Location and planogram

| ID | Scenario | Behaviour |
|---|---|---|
| EC-19 | SKU has no planogram entry | Show availability, state the location is unknown rather than inventing one |
| EC-20 | SKU has several locations | Show all; route to the nearest. The normal case, not an exception |
| EC-21 | Planogram references an aisle absent from the store graph | Data integrity failure, caught by startup validation, not at request time |
| EC-22 | Locked cabinet — spirits, formula, razor blades | Location type `ASSISTED`: route to the cabinet, state a colleague must unlock it. FR-12 and AC-16 |
| EC-23 | Behind a counter — deli, pharmacy, fish | Location type `COUNTER`: route to the counter, no rack or shelf |
| EC-24 | Seasonal bay currently empty | Flagged seasonal; suppressed at zero stock so shoppers aren't sent to bare shelving |

### 6.4 Routing

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

### 6.5 Orchestration

| ID | Scenario | Behaviour |
|---|---|---|
| EC-34 | Clarification abandoned, interrupt never resumed | Nothing to clean up: every request runs on a fresh thread, deleted before the response is sent (§4.1). LangGraph does not expire threads on its own, so nothing may outlive its request |
| EC-35 | Clarify loop never converges | Loop counter in state, capped at two rounds, then forced to return the ranked list |
| EC-36 | The same search from two tabs at once | Independent: no request shares a thread with another, and each tab holds its own answers and basket |
| EC-37 | Model call times out or errors | Every model node has a deterministic fallback: keyword search, a static substitution table, a directions template. The journey always completes |
| EC-38 | Model returns malformed structured output | Validate against the schema; fall back to keyword search. Strict mode makes this rare, not impossible — a reply cut off at the token cap still fails |
| EC-39 | Model declines the request | Check the stop reason before reading content; fall through to the deterministic path |
| EC-40 | Node raises mid-graph, partial state | The checkpoint holds the last good state; resume from the failed node rather than restarting |
| EC-47 | `verify` finds a claim that does not match the service result | The composed answer is discarded, never corrected in place. The deterministic template is rendered from the service results instead and the discrepancy is recorded in `degraded`. A mismatch is a bug to surface, not a difference to split |
| EC-41 | Page is refreshed mid-journey | The basket and start point survive in the tab's session storage; a pending clarification is simply asked again by re-running the search. Nothing is lost on the server, because nothing was kept there |

### 6.6 Data and startup

| ID | Scenario | Behaviour |
|---|---|---|
| EC-42 | Malformed store graph | Fail at startup with a clear error. Never serve a half-loaded graph |
| EC-43 | Planogram references SKUs absent from the catalogue | Startup validation lists the orphans and refuses to start |
| EC-44 | Disconnected graph components | Connectivity check at startup. A store you cannot walk across is a data bug, not a routing edge case |
| EC-45 | Zero or negative edge weight | Rejected at load. Negative weights break Dijkstra's correctness guarantee outright |

---

### 6.7 Barcode scan

| ID | Scenario | Behaviour |
|---|---|---|
| EC-48 | Camera declined, revoked after a scan, absent, or blocked because the page is on plain HTTP (C-08) | The digits field beside the camera is the same lookup and keeps working; nothing about the search depends on the camera |
| EC-49 | No readable barcode in view — damaged, creased, partly covered, blurred, too far away | The camera keeps looking; after a few seconds with nothing read the page says what to try, and the digits field is always there. Never a guess at what it might have been |
| EC-50 | A valid barcode that is not in this catalogue | Said plainly, with no nearest match and no suggestions (AC-28). It may be another shop's product or not a grocery product at all |
| EC-51 | A barcode that is not a product's — a QR code, a shipping label | Not read: only retail symbologies are decoded, so it reports as no barcode found |
| EC-52 | Mistyped digits — wrong length, or a failed check digit | "That isn't a valid barcode", before any lookup. A near-miss number is never matched to the closest real one |
| EC-53 | Two different barcodes in one frame | Neither is chosen: the shopper is asked to scan one product at a time, and the camera keeps looking. The same code twice is one code |
| EC-54 | The camera keeps seeing the same barcode after it is read | Looked up once: the camera stops at the first read. Scanning again, or typing digits, is a new lookup |

### 6.8 Stock alerts

| ID | Scenario | Behaviour |
|---|---|---|
| EC-55 | A product goes from low to out in one update | One out-of-stock alert. The low alert it already had is not repeated |
| EC-56 | A product recovers, or stays low or out | Nothing is sent |
| EC-57 | A product is not stocked at this branch (`ranged=false`) | Never alerted: it was never on the shelf to run out |
| EC-58 | The mail service fails or rejects the send | The job fails and shows it in GitHub; re-running it sends once, by the idempotency key. The website is unaffected |
| EC-59 | The secrets are missing | The job stops with a message naming the missing setting, and sends nothing. A dry run prints the emails instead |
| EC-60 | An update makes no product cross a threshold | No email at all — not an empty one |

### 6.9 Voice input

| ID | Scenario | Behaviour |
|---|---|---|
| EC-61 | Microphone declined, absent, blocked because the page is on plain HTTP (C-08), or the browser's speech service cannot be reached | Said in one line — type instead — and the search box keeps working; nothing about the search depends on the microphone |
| EC-62 | A browser with no speech recogniser | No microphone is offered; the page is the typed page |
| EC-63 | Nothing heard — silence, or only the noise of the store | "Didn't catch that", and no search is run. Never a guess at what was meant |
| EC-64 | A word misheard | The search runs on what was heard, which stays in the box: the result is what typing those words would give, and the shopper corrects it by typing |

### 6.10 Suggestions

| ID | Scenario | Behaviour |
|---|---|---|
| EC-65 | One letter typed, or nothing in the catalogue begins with what was typed | No list; Search still searches exactly what was typed, and says what it does not recognise as before |
| EC-66 | A product not sold at this store, or one sold out | The first is never suggested — the search still answers "not sold here" (EC-04). A sold-out one is suggested, marked sold out |
| EC-67 | Typing the next item of a list — "milk, bre" | Suggestions are for "bre" only; choosing one keeps "milk, " and replaces just that item |

## 7. Onboarding a new store

FR-25 says a different store is a replaced set of data files and no code changes. This
is what that costs in practice, and it is the honest answer to "could we run
this in a real branch?"

| What a store supplies | What has to happen to it |
|---|---|
| Planogram as a spreadsheet | Rename and normalise columns, fix bay and shelf numbering, join product details, and attach every placement to a map point. Scripted, roughly a day for a first store |
| Planogram as a PDF or images | Table extraction, then a person checks every row. Not attempted here, and the reason this is a data problem rather than a software one |
| Floor plan as an image or CAD | Someone marks the walkable points and the paths between them, once per floor, and sets the scale. CAD gives exact coordinates; an image needs tracing |
| Stock | Synthetic here. A live feed replaces one service, because nothing above the service layer knows where stock comes from |

**The link people forget:** every rack in the planogram must name a point on
the map. Without it the system can tell a shopper the aisle but cannot route
them to it — the planogram and the map are two separate things, and the join
between them is what makes a location walkable.

The running system never reads a PDF or an image. Conversion happens once,
before the store folder exists, and the validator refuses the folder if the
result is inconsistent (NFR-07).

---

## 8. Where this design is weakest

Say these before someone finds them.

**A planogram says where a product is *supposed* to be.** Shelves drift from
plan within days of a range change. Synthetic data hides this completely, so the
demo will look more reliable than a real deployment would. Honest mitigations
are a user "this is wrong" report and, longer term, vision-based shelf
compliance.

**The start point is self-reported.** FR-15 has the shopper pick a floor and an
aisle, because live positioning is out of scope. A shopper who picks the wrong
aisle gets a correct route from the wrong place, and nothing in the system can
detect it.

**Substitutes are limited by what the catalogue records.** FR-09 filters
candidates on dietary attributes before the model sees them, so an unrecorded
attribute reads as unknown and the candidate is excluded. That is the safe
direction to fail, but it means thin catalogue data produces thin substitutes.

**One store, one shopper.** No concurrency, no live stock feed, no second store
running at the same time. The portability test (AC-09) swaps the data files; it
does not run two stores at once.
