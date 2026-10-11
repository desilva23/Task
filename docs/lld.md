# Low-Level Design

Rendered: **https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf**
Companions: [HLD](https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB) · [architecture note](https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C)

All three are private — share from each page's Share menu.

---

## 1. Module layout

```
backend/
  main.py                 app factory, lifespan: load → validate → build matrices
  config.py               every threshold and cap, one place (§13)
  api/
    journey.py            POST /journey, POST /journey/resume, GET /journey/{id}
    route.py              POST /route
    store.py              GET /store/{id}/aisles, GET /store/{id}/graph
    sse.py                node-event stream
  graph/
    build.py              StateGraph assembly, checkpointer, compile
    state.py              JourneyState TypedDict + reducers
    routers.py            conditional-edge functions
    nodes/                classify · understand · resolve_items · clarify
                          availability · substitutes · locations
                          route_single · route_multi · describe
  services/
    catalogue.py          Catalogue — product store + BM25 index
    planogram.py          Planogram — sku → [Placement]
    stock.py              Stock — batched position lookup
    routing.py            RouteEngine — matrices, path reconstruction, TSP
    storegraph.py         StoreGraph — nodes, edges, adjacency
  models/
    domain.py             Product, Placement, StockPosition, Location, Route
    llm.py                ParsedQuery, SubstituteChoice (structured outputs)
    api.py                request/response models
  errors.py               error taxonomy (§12)
  validation.py           startup checks (§13)
data/
  SBY-DEMO-001/           store.csv  products.csv  stock.csv
                          planogram.csv  map_nodes.csv  map_edges.csv  (schema.md §1)
frontend/
  index.html  app.js  store-map.svg
tests/
  unit/  integration/  fixtures/
```

**One rule the layout enforces:** `graph/nodes/*` may import from `services/*`,
never the reverse, and `services/*` never imports `langchain` or `langgraph`.
That keeps the deterministic core testable without a graph runtime and without a
model — which is what makes the fallbacks in §6 honest rather than aspirational.

---

## 2. Identifier scheme

**Moved to [`schema.md`](schema.md) §3.** An identifier is a data format, so it
belongs with the schema.

It is unchanged where the two overlap, and extends with three node types this
document never gave a format to — `counter`, `cabinet` and `bin`. §3 below
required `location_type` values of `COUNTER`, `ASSISTED` and `DUMP_BIN` that had
to route *somewhere*, and a deli counter is not a rack.

---

## 3. Data file schemas

**Moved to [`schema.md`](schema.md) §4.** This section described four JSON
files. The data is six CSVs, so nothing of it survives but the reasoning, which
moved with it:

| Was here | Now in `schema.md` |
|---|---|
| `products.json`, and why `null` is not `false` | §4.2, and §2.2 — which is the same argument made harder, because CSV has no null and an empty cell reads as `NaN` |
| `planogram.json`, the `location_type` table | §4.4, plus a node-compatibility matrix this section had no way to express |
| `stock.json`, and why `ranged` is load-bearing | §4.3 |
| `store_graph.json`, and why the lift penalty is in metres | §4.5 and §4.6 |

**Both sections are kept as numbered stubs rather than cut out.** Renumbering
§4–§15 would break every cross-reference to them from `hld.md`, `schema.md`,
`CLAUDE.md` and §1 of this document — and a moved decision keeps a trail, the
same convention the requirements register follows for a resolved question.

---

## 4. Graph construction and matrices

```python
class StoreGraph:
    nodes: dict[str, Node]          # id → Node
    index: dict[str, int]           # id → matrix row/col
    rev:   list[str]                # matrix index → id

class RouteEngine:
    D_full: np.ndarray              # (V, V) float64 — distances, all edges
    P_full: np.ndarray              # (V, V) int32   — predecessors
    D_step: np.ndarray              # same, lift-only subgraph
    P_step: np.ndarray

    def build(self, g: StoreGraph) -> None: ...
    def distance(self, u: str, v: str, step_free: bool = False) -> float: ...
    def path(self, u: str, v: str, step_free: bool = False) -> list[str]: ...
    def invalidate(self, disabled: list[EdgeRef]) -> None: ...   # EC-30
```

Build:

```python
csr  = build_csr(g)                 # effective weight = weight_m + penalty_m
D, P = shortest_path(csr, method="D", directed=True, return_predecessors=True)
```

Path reconstruction:

```python
def path(self, u, v, step_free=False):
    P = self.P_step if step_free else self.P_full
    i, j = self.g.index[u], self.g.index[v]
    if i == j:
        return [u]                                  # EC-25, zero-length
    if P[i, j] == NO_PATH:                          # NO_PATH = -9999
        raise UnreachableNodeError(u, v)            # EC-29
    out, k = [v], j
    while k != i:
        k = int(P[i, k])
        out.append(self.g.rev[k])
    return list(reversed(out))
```

| Quantity | Value |
|---|---|
| Nodes V | ~300 (216 racks + aisle ends + cross-aisle + 6 cores + entrance + tills) |
| Edges E | ~700, directed |
| Build cost | ~1M operations per run, two runs, well under a second |
| Memory | D 720 KB + P 360 KB per matrix, ~2 MB for both pairs |
| Query cost | `distance` O(1); `path` O(len), ~15 hops |

---

## 5. Graph state

```python
class JourneyState(TypedDict):
    # request, written once
    store_id:   str
    raw_query:  str
    mode:       Literal["auto", "single", "multi"]
    start_node: str
    step_free:  bool

    # classification
    shape:  Literal["too_short", "digits", "batch", "nl", "term"]
    terms:  list[SearchTerm]                 # {text, qty}
    parsed: ParsedQuery | None

    # resolution
    candidates:  dict[str, list[Product]]    # term → ranked candidates
    resolved:    dict[str, str]              # term → chosen SKU
    unresolved:  list[str]                   # matched nothing — EC-08
    not_ranged:  list[str]                   # real but not stocked here — EC-04

    # availability and location
    availability: dict[str, StockPosition]
    locations:    dict[str, list[Placement]]
    substitutes:  dict[str, list[Product]]

    # basket — the input to routing
    basket: Annotated[list[BasketItem], merge_basket]

    # output
    route:      Route | None
    directions: list[str]

    # control
    clarify_rounds: int                                 # capped at 2 — EC-35
    degraded:  Annotated[list[str], operator.add]       # nodes that fell back
    errors:    Annotated[list[JourneyError], operator.add]
```

Three fields earn their place:

- **`basket`** carries a custom reducer rather than `operator.add`, because two
  concurrent adds of the same SKU must merge quantities instead of producing a
  duplicate row (EC-07).
- **`degraded`** records every node that used its fallback, and the response
  carries it — so a demo that quietly ran without a model is visible rather
  than mysterious.
- **`clarify_rounds`** is what makes the cycle terminate.

---

## 6. Node contracts

| Node | Reads | Writes | Fallback on failure |
|---|---|---|---|
| `classify_query` | raw_query | shape, terms | n/a — pure function |
| `understand_query` | raw_query | parsed, terms | treat whole query as one term; append to `degraded` |
| `resolve_items` | terms, parsed | candidates, resolved, unresolved, not_ranged | n/a — deterministic |
| `clarify` | candidates, clarify_rounds | resolved, clarify_rounds | after 2 rounds auto-pick rank 1 and note it |
| `check_availability` | resolved | availability | mark unknown, never guess — EC-18 |
| `suggest_substitutes` | availability, locations | substitutes | static same-category in-stock list |
| `resolve_locations` | resolved | locations | n/a — deterministic |
| `route_single` | basket, start_node, step_free | route | surface the error, no partial route |
| `route_multi` | basket, start_node, step_free | route | floor-ordered serpentine without 2-opt |
| `describe_route` | route, locations | directions | template per hop; append to `degraded` |

Routers:

```python
def after_classify(s) -> str:
    if s["shape"] in ("too_short", "digits"): return END       # EC-01, EC-10
    if s["shape"] == "nl":        return "understand_query"
    return "resolve_items"

def after_resolve(s) -> str:
    if not s["resolved"] and not s["candidates"]: return END   # EC-03
    if s["clarify_rounds"] < MAX_CLARIFY_ROUNDS and needs_clarification(s):
        return "clarify"                                       # EC-05
    return "check_availability"

def after_availability(s) -> str:
    return "suggest_substitutes" if any_out_of_stock(s) else "resolve_locations"

def after_locations(s) -> str:
    routable = [i for i in s["basket"] if i.routable]
    if not routable:                                return END          # EC-15
    if len(routable) == 1 or s["mode"] == "single":  return "route_single"  # EC-28
    return "route_multi"
```

---

## 7. Service interfaces

```python
class Catalogue:
    def by_sku(self, sku: str) -> Product | None: ...
    def search(self, term: str, filt: QueryFilter | None, limit: int) -> list[Scored]: ...
    def by_category(self, category: str) -> list[Product]: ...

class Planogram:
    version: str
    def for_sku(self, sku: str) -> list[Placement]: ...                    # may be [] — EC-19
    def for_skus(self, skus: list[str]) -> dict[str, list[Placement]]: ... # BATCHED

class Stock:
    as_of: datetime
    def positions(self, skus: list[str]) -> dict[str, StockPosition]: ...  # BATCHED
```

Both multi-item lookups are list-in / map-out from the start. At POC scale the
body is a comprehension; against a real stock service the signature is the
difference between one request and sixty, and changing it later means changing
every caller.

---

## 8. Search internals

### 8.1 Index construction

```python
def searchable_text(p: Product) -> str:
    return " ".join([p.name, p.brand, p.size, p.aisle_category, *p.synonyms])

def normalise(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = t.lower()
    t = re.sub(r"[^a-z0-9%.]+", " ", t)   # keep digits, % and . for "500ml", "1.5l"
    return [tok for tok in t.split() if tok not in STOPWORDS]

index = BM25Okapi([normalise(searchable_text(p)) for p in products], k1=1.2, b=0.5)
```

`b=0.5` rather than the usual 0.75: `b` controls how hard a long document is
penalised, and product names are all short, so the standard value over-penalises
the ones that happen to carry synonyms. Both constants belong on the eval set,
not in a reviewer's opinion.

### 8.2 Query classification

```python
SPLIT  = re.compile(r"[,;\n]|\s+and\s+|\s*\+\s*", re.I)
DIGITS = re.compile(r"^\d{8,13}$")
QTY    = re.compile(r"^(\d+)\s*(?:x|×)?\s+(.+)$", re.I)
NL_CUE = re.compile(r"\b(for|with|need|want|make|making|something|what|how|recipe)\b", re.I)

def classify(raw: str) -> tuple[str, list[SearchTerm]]:
    q = " ".join(raw.split())
    if len(q) < MIN_QUERY_CHARS:  return "too_short", []
    if DIGITS.match(q):           return "digits", []          # not a product request
    parts = [p.strip() for p in SPLIT.split(q) if p.strip()]
    if len(parts) > 1:
        return "batch", [parse_qty(p) for p in parts[:MAX_BATCH_TERMS]]   # EC-06
    if len(q.split()) > NL_WORD_THRESHOLD and NL_CUE.search(q):
        return "nl", []
    return "term", [parse_qty(q)]
```

**Order matters, and one rule is deliberately crude.** `" and "` splits before
the natural-language test, so `"milk and bread"` is a batch of two rather than a
sentence. The cost: a product with "and" in its name splits wrongly — "salt and
vinegar crisps" becomes two terms. The mitigation is cheap: if a split part
fails to resolve, retry the unsplit string once before reporting it unresolved.
Worth stating, because a reviewer will find this example.

### 8.3 Ranking

```python
def rank(cands: list[Scored], term: str, stock: dict) -> list[Scored]:
    return sorted(cands, key=lambda c: (
        not stock[c.sku].ranged,          # ranged first — a hard gate
        stock[c.sku].shelf_qty == 0,      # in stock before out of stock
        not variant_match(c.product, term),
        -c.bm25,
        -c.product.popularity,
        not c.product.own_brand,
    ))
```

A lexicographic tuple sort, not a weighted sum. Weighted sums need tuning and
cannot be explained — "why did this rank third" has no short answer. A tuple
sort is a precedence list a buyer can read, and it cannot be accidentally
mis-tuned into putting an unstocked product first.

### 8.4 Ambiguity test

```python
def needs_clarification(cands: list[Scored]) -> bool:
    if len(cands) < AMBIGUITY_MIN_HITS: return False
    top, second = cands[0].bm25, cands[1].bm25
    if top <= 0:                        return False
    return (top - second) / top < AMBIGUITY_MARGIN     # 0.15
```

A *relative* margin, because BM25 scores are unnormalised and vary with query
length — an absolute threshold would fire inconsistently between a one-word and
a three-word query.

---

## 9. Structured output models

```python
class ParsedQuery(BaseModel):
    """Note what is absent: no sku, no product_name. The model cannot name a
    product, because the schema gives it nowhere to put one."""
    model_config = ConfigDict(extra="forbid")
    items:             list[str] = Field(default_factory=list, max_length=MAX_BATCH_TERMS)
    department:        list[str] = Field(default_factory=list)
    aisle_category:    list[str] = Field(default_factory=list)
    dietary_required:  list[str] = Field(default_factory=list)
    exclude_allergens: list[str] = Field(default_factory=list)

class SubstituteChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku:    str      # validated against the candidate set
    reason: str = Field(max_length=140)
```

```python
candidates = [p for p in catalogue.by_category(cat)
              if stock[p.sku].shelf_qty > 0
              and dietary_compatible(p, original)]      # filter BEFORE the model

choice = model.with_structured_output(SubstituteChoice).invoke(prompt(candidates))
if choice.sku not in {p.sku for p in candidates}:
    raise GroundingError(choice.sku)                    # fall back, never surface
```

**The guardrail is code, not prose.** Two mechanisms, both enforced rather than
requested. The schema has no field for a product name, so query understanding
cannot invent one. And a substitute SKU that was not in the candidate list the
service built is rejected outright — the model picks *among* safe options, it
does not nominate them.

`dietary_compatible` treats a `null` flag as incompatible when the original
product required it. An unknown value never satisfies a dietary requirement.

---

## 10. Routing internals

### Single

```python
def route_single(start, placements, step_free):
    target = min(placements, key=lambda p: engine.distance(start, p.node_id, step_free))
    nodes  = engine.path(start, target.node_id, step_free)
    return Route(nodes=nodes,
                 distance_m=engine.distance(start, target.node_id, step_free),
                 floors=floors_touched(nodes),
                 placement=target)
```

When a SKU has several placements (EC-20) the nearest wins — which is why
`distance` being O(1) matters: evaluating four candidate locations is four array
reads.

### Multi — floor-clustered, open path per floor, closed at the tills

```python
def route_multi(start, items, end_node, step_free):
    chilled, ambient = partition(items, lambda i: i.location_type == "CHILLER")
    groups = group_by_floor(ambient)                   # {level: [Placement]}
    order  = sorted(groups, reverse=True)              # highest floor first
    legs, cursor = [], start

    for level in order:
        entry = nearest_core(cursor, level, step_free) # arrive at the cheaper core
        seq   = nn_then_2opt(entry, groups[level], step_free)
        legs += [engine.path(cursor, entry, step_free)] + stitch(seq)
        cursor = seq[-1].node_id if seq else entry

    for p in chilled_last(chilled):                    # EC-33
        legs.append(engine.path(cursor, p.node_id, step_free)); cursor = p.node_id

    legs.append(engine.path(cursor, end_node, step_free))   # FR-11, the tills
    return Route(nodes=dedupe_joins(legs), ...)
```

### nn_then_2opt — open path, fixed start

```python
def nn_then_2opt(entry, stops, step_free):
    seq, pool, cur = [], list(stops), entry
    while pool:                                        # nearest neighbour
        nxt = min(pool, key=lambda p: engine.distance(cur, p.node_id, step_free))
        seq.append(nxt); pool.remove(nxt); cur = nxt.node_id

    improved = True
    while improved:                                    # 2-opt, OPEN variant
        improved = False
        for i in range(len(seq) - 1):
            for j in range(i + 2, len(seq)):
                if delta(seq, i, j, entry) < -EPSILON: # no wrap-around term
                    seq[i+1:j+1] = reversed(seq[i+1:j+1])
                    improved = True
    return seq
```

**Open-path 2-opt, not the textbook version.** Standard 2-opt optimises a closed
tour and its gain calculation includes the edge back to the origin. Each floor
leg here is an *open* path with a fixed start and a free end, so the wrap-around
term must be dropped from `delta`. Using the closed-tour formula produces routes
that look subtly wrong — usually a last stop that doubles back — and it is an
easy mistake to ship.

---

## 11. API contracts

```jsonc
POST /journey
{ "store_id": "SBY-DEMO-001",
  "query":      "milk, bread, eggs",
  "mode":       "auto",
  "start_node": "F0-A01-S",
  "thread_id":  null,
  "step_free":  false }

200 →
{ "thread_id": "th_01J...",
  "status":    "complete" | "awaiting_input",
  "shape":     "batch",
  "results": [
    { "term": "milk", "status": "available",
      "product":   { "sku": "...", "name": "...", "size": "...", "price_gbp": 1.45 },
      "stock":     { "shelf_qty": 14, "as_of": "..." },
      "locations": [{ "node_id": "F0-A04-R02", "shelf": 1, "facing": 2,
                      "location_type": "HOME",
                      "label": "Floor 0 · Aisle 4 · Rack 2 · eye level" }],
      "routable":  true },
    { "term": "chicken thighs", "status": "out_of_stock",
      "substitutes": [{ "sku": "...", "name": "...", "reason": "..." }],
      "routable": false }
  ],
  "clarification": null,
  "route":         null,
  "degraded":      [] }
```

```
POST /journey/resume    { "thread_id": "...", "value": { "term": "bread", "sku": "..." } }
POST /route             { "thread_id": "...", "skus": [...], "start_node": "...", "step_free": false }
GET  /journey/{id}      → last completed state      (EC-41, survives an SSE drop)
GET  /store/{id}/aisles → picker options, grouped by floor
GET  /store/{id}/graph  → nodes + edges for the map
```

SSE:

```
event: node
data: {"node":"check_availability","status":"done","elapsed_ms":12}

event: result
data: { ...the 200 body above... }
```

`/journey` returns **results only** — never a route. Routing is `/route`, called
from the basket, which is what FR-16 requires: nothing is routed until the
shopper has moved the available items across.

---

## 12. Error taxonomy

| Error | Raised when | Handling |
|---|---|---|
| `StoreDataError` | Startup validation fails | **Refuse to start.** Never serve a half-loaded store |
| `UnknownStoreError` | store_id not loaded | 404 |
| `InvalidNodeError` | start_node absent from the graph | 400, name the valid picker options |
| `UnreachableNodeError` | Predecessor matrix says NO_PATH | 500 + log as a data bug. Should be impossible after §13 |
| `ModelUnavailableError` | Timeout, 429, 5xx, refusal stop reason | Caught in the node; deterministic fallback; append to `degraded` |
| `SchemaValidationError` | Structured output fails the model | Same. Known interaction with thinking enabled |
| `GroundingError` | Model named a SKU outside the candidate set | Never surfaced. Drop the suggestion, log loudly |

The split that matters: a **data** error stops the service, a **model** error
degrades one node. Nothing in the second class can produce a wrong location or a
wrong stock figure, because no model sits on those paths.

---

## 13. Startup validation

Run in the FastAPI lifespan, before the first request is accepted.

| # | Check | Catches |
|---|---|---|
| 1 | Every edge endpoint exists in `nodes` | Typo in a hand-authored graph |
| 2 | Every `weight_m` > 0; every `penalty_m` ≥ 0 | EC-45 — negative weights break Dijkstra's guarantee |
| 3 | Graph strongly connected across all floors | EC-44, EC-29 |
| 4 | Every floor reachable from `F0-ENTRANCE` | A floor with no working core |
| 5 | Lift-only subgraph also connected | EC-31 — step-free routing that silently has no answer |
| 6 | Every placement `node_id` exists in the graph | EC-21 |
| 7 | Every placement `sku` exists in the catalogue | EC-43 |
| 8 | Every stock `sku` exists in the catalogue | Stale stock extract |
| 9 | At least one `F0-TILL-*` node | FR-11 has no terminus |
| 10 | `min_level`/`max_level` agree with node levels | Map and data disagreeing about the building |
| 11 | Every `ASSISTED`/`COUNTER` placement has no shelf set | A counter with a shelf number is a modelling error |

---

## 14. Configuration

```python
MIN_QUERY_CHARS     = 2       # EC-01
MAX_BATCH_TERMS     = 30      # EC-06
NL_WORD_THRESHOLD   = 4
BM25_K1, BM25_B     = 1.2, 0.5
SEARCH_LIMIT        = 10
FUZZY_THRESHOLD     = 80      # rapidfuzz ratio
FUZZY_TRIGGER_SCORE = 2.0     # BM25 below this triggers the fuzzy retry
AMBIGUITY_MIN_HITS  = 3
AMBIGUITY_MARGIN    = 0.15    # §8.4
MAX_CLARIFY_ROUNDS  = 2       # EC-35
THREAD_TTL_MINUTES  = 30      # EC-34 — abandoned interrupts
MODEL_TIMEOUT_S     = 6
NO_PATH             = -9999   # scipy sentinel
EPSILON             = 1e-9

MODEL_UNDERSTAND    = "claude-haiku-5-5"
MODEL_SUBSTITUTE    = "claude-opus-5-5"
MODEL_DESCRIBE      = "claude-haiku-5-5"
```

Every number a reviewer might question lives here with the edge case it serves
in the comment. `THREAD_TTL_MINUTES` drives the sweep that stops abandoned
clarifications accumulating checkpoints forever — LangGraph does not expire
threads on its own.

---

## 15. Test plan

| Layer | Covers | Representative cases |
|---|---|---|
| Unit · classify | Every branch of §8.2 | Empty · 1 char · digits only · `"milk, bread"` · `"milk and bread"` · `"salt and vinegar crisps"` (the known-crude case) · `"2 x milk"` · 200 terms |
| Unit · search | Ranking precedence | Unstocked never outranks stocked · exact size wins · typo resolves via fuzzy · category query detected |
| Unit · routing | Matrix and reconstruction | Same-node route returns `[u]` · known-distance pair · NO_PATH raises · step-free matrix differs where it should |
| Unit · TSP | Open-path correctness | Single stop returns unchanged · 2-opt never lengthens a route · chilled last · ends at a till |
| Unit · grounding | §9 guardrails | Out-of-set SKU raises `GroundingError` · `null` dietary flag never satisfies a requirement |
| Integration · graph | Edge routing and cycles | Ambiguous term interrupts then resumes · clarify caps at 2 · all-out-of-stock reaches END without a route · single item in multi mode takes the single path |
| Integration · fallback | §6 fallback column | Each model node forced to fail; journey still completes and `degraded` names it |
| Validation | §13 | One fixture per check, each expected to refuse startup |

**The test that matters most** is the fallback suite. It is the only thing that
proves the claim the whole design rests on — that a model failure degrades
fluency and never correctness. Forcing each of the three model nodes to fail and
asserting the journey still returns a correct location and a correct route is
what turns that from an assertion into a fact.
