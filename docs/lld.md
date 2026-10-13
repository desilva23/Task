# Low-Level Design

Rendered: **https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf**
Companions: [HLD](https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB) · [architecture note](https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C)

All three are private — share from each page's Share menu.

---

## 1. Module layout

```
app.py                    Streamlit entry point — the only executable
config.py                 every threshold and cap, one place (§14)
ui/
  search.py               the st.form search box and the position picker
  results.py              grouped results and the basket gate action
  floorplate.py           one SVG plate per floor, route overlay, markers
  directions.py           the ordered directions list — the accessible route
  resources.py            @st.cache_resource builders: store, index, matrices
graph/
  build.py                StateGraph assembly, checkpointer, compile
  state.py                JourneyState TypedDict + reducers
  routers.py              conditional-edge functions
  nodes/                  classify · understand · resolve_items · clarify
                          availability · substitutes · locations
                          route_single · route_multi · describe · verify
services/
  catalogue.py            Catalogue — product store + BM25 index
  planogram.py            Planogram — sku → [Placement]
  stock.py                Stock — batched position lookup
  routing.py              RouteEngine — matrices, path reconstruction, TSP
  storegraph.py           StoreGraph — nodes, edges, adjacency
  basket.py               Basket — SKUs added across searches; routability re-checked per call
  multistop.py            route_multi — floor order, open-path 2-opt, ends at a till (§10)
models/
  domain.py               Product, Placement, StockPosition, Location, Route
  llm.py                  ParsedQuery, SubstituteChoice (structured outputs)
errors.py                 error taxonomy (§12)
validation.py             startup checks (§13)
data/
  SBY-DEMO-001/           store.csv  products.csv  stock.csv
                          planogram.csv  map_nodes.csv  map_edges.csv  (schema.md §1)
datagen/                  seeded generator for the synthetic demo store (schema.md §8)
tests/
  unit/  integration/  fixtures/
```

**Two rules the layout enforces.** `graph/nodes/*` may import from `services/*`,
never the reverse, and `services/*` never imports `langchain` or `langgraph` —
which keeps the deterministic core testable without a graph runtime and without
a model, and is what makes the fallbacks in §6 honest rather than aspirational.
And nothing below `ui/` imports `streamlit`: the page is the only module that
knows it is a page, so putting a service in front of the same graph later
changes nothing underneath it.

There is no `api/` package and no separate frontend. `app.py` calls the compiled
graph in the same process (C-03), so no module in this tree imports a web
framework.

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
    verified:  bool                                     # set by verify — EC-47
    mismatches: Annotated[list[Mismatch], operator.add] # claim, expected, found
```

Three fields earn their place:

- **`basket`** carries a custom reducer rather than `operator.add`, because two
  concurrent adds of the same SKU must merge quantities instead of producing a
  duplicate row (EC-07).
- **`degraded`** records every node that used its fallback, and the response
  carries it — so a demo that quietly ran without a model is visible rather
  than mysterious.
- **`clarify_rounds`** is what makes the cycle terminate.
- **`verified`** is false until `verify` has passed the composed answer. The
  page renders nothing while it is false, which is how NFR-02 becomes a
  property of the state machine rather than a discipline.

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
| `verify` | directions, route, locations, availability, resolved | verified, mismatches | n/a — deterministic. A mismatch discards the composed text and re-renders the template (EC-47) |

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

`describe_route → verify → END` is a plain edge, not a conditional one, and
`verify` has no outgoing branch that skips it. That is deliberate: a
conditional edge is a decision someone can get wrong, and there must be no path
from a composed answer to the page that does not pass the gate.

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

### 7.1 Class model

Five service classes own collections of value types. Two foreign-key joins carry
the whole design.

```
   Catalogue          Planogram          Stock          StoreGraph      RouteEngine
   by_sku()           for_sku()          positions()    validate()     distance()
   search()           for_skus()         + as_of        subgraph()     path()
   by_category()      + version                             ▲          ◄── reads
       │ 1..*             │ 1..*             │ 1..*          │ 1..*
       ▼                  ▼                  ▼               ▼       ▼ 1..*
  ┌─────────┐      ┌───────────┐     ┌──────────────┐    ┌──────┐ ┌──────┐
  │ Product │◄─sku─│ Placement │─node│ StockPosition│    │ Node │ │ Edge │
  │  PK sku │ 0..* │  THE JOIN │ _id │              │    │  PK  │ │      │
  └────┬────┘      └─────┬─────┘  1  └──────┬───────┘    └──▲───┘ └──────┘
       │ 1                │                 │                │
       ▼                  └────── node_id ──┼────────────────┘
  ┌──────────────────────────┐              │
  │ Dietary                  │     sku, same domain
  │ gluten_free: bool | None │◄─────────────┘
  │ None = unchecked         │
  └──────────────────────────┘
```

| Join | Cardinality | Why it matters |
|---|---|---|
| `Placement.sku` → `Product.sku` | **0..\* placements per product** | A SKU sits on its home rack *and* a promo end cap. Also permits zero — catalogued but not placed (EC-19) |
| `Placement.node_id` → `Node.node_id` | exactly 1 | Every placement is somewhere walkable. Checked at load |

The one-to-many on the first is the structural reason `Placement` is a separate
type rather than fields on `Product`. Collapsing them breaks FR-11.

`Dietary`'s `bool | None` fields are the type-level expression of *empty is not
FALSE*: `None` means unchecked and never satisfies a filter.

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
    q = tidy(raw)          # collapse spaces per line — keep newlines, they separate items
    if len(q) < MIN_QUERY_CHARS:  return "too_short", []
    if DIGITS.match(q):           return "digits", []          # not a product request
    parts = [p.strip() for p in SPLIT.split(q) if p.strip()]
    if len(parts) > 1:
        return "batch", [parse_qty(p) for p in parts[:MAX_BATCH_TERMS]]   # EC-06
    if len(q.split()) > NL_WORD_THRESHOLD and NL_CUE.search(q):
        return "nl", []
    return "term", [parse_qty(q)]
```

**Order matters, and one rule needs a guard.** `" and "` splits before the
natural-language test, so `"milk and bread"` is a batch of two rather than a
sentence. Split blindly, a product with "and" in its name breaks: "salt and
vinegar crisps" becomes "salt" and "vinegar crisps" — and both resolve, to
table salt and the crisps, so a retry-on-failure never fires. The guard runs
**before** the split: when the query divides only on "and", it stays one term if
a single product's name contains every one of its words. "Salt & Vinegar
Crisps" and "Sweet & Sour Sauce" stay whole; "milk and bread" still splits,
because no product is named after both.

### 8.2a Fuzzy retry and categories

When the best BM25 score is below `FUZZY_TRIGGER_SCORE`, search retries once:

1. Correct each query word to the nearest word in the catalogue's own
   vocabulary (`rapidfuzz` ratio ≥ `FUZZY_THRESHOLD`) and rerun BM25 —
   "paracetomol" becomes "paracetamol", and ranking still explains itself.
2. If that finds nothing, match the query against whole product names with
   `WRatio` ≥ `FUZZY_THRESHOLD` — which catches run-together words such as
   "cocacola".

A term equal to a department or category name that no product is named after
("dairy", "frozen") returns the **category** rather than an arbitrary SKU
(EC-09). "Bread" and "milk" are product names too, so they search as products
and come back ambiguous (EC-05).

A sentence-shaped query searched by keywords — the fallback when the model is
unavailable (EC-37) — is **never marked resolved**. Keyword-matching a sentence
is a guess, so its best matches are offered as a choice instead.

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

Each rule has a name — *carried here*, *in stock*, *size asked for*, *text
match*, *popularity*, *own brand* — and `explain` reports, for every result after
the first, the first rule that separates it from the one above (NFR-09, AC-26).

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

### The verify pass

The two mechanisms above stop the model *inventing* a fact. `verify` catches
everything downstream of that — a stale cached figure, a mis-joined placement,
a template that formatted the wrong leg. Five checks, all against state the
services produced:

```python
def verify(s: JourneyState) -> list[Mismatch]:
    m = []
    # 1 every SKU named in the answer was resolved by the search
    # 2 floor, aisle, rack and shelf equal the Placement for that SKU
    # 3 availability wording equals the StockPosition; an unavailable
    #   item has no stop in the route
    # 4 each leg distance and the total equal the plan within ROUND_TOLERANCE_M,
    #   and the floor-change count matches the connectors in the node path
    # 5 every aisle or landmark named in a step appears in the plan's node path
    return m
```

A non-empty list discards the composed text. The template is rendered from the
same service results, `verified` is set on that, and the mismatch is recorded —
never patched in place. Patching would hide the bug that produced it.

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
def route_multi(start, stops, step_free):
    order  = sorted({s.level for s in stops}, reverse=True)   # highest floor first
    seq, cursor = [], start
    for level in order:
        entry = nearest_core(cursor, level, step_free)        # arrive at the cheaper core
        here  = [s for s in stops if s.level == level]
        ambient, chilled = partition(here, lambda s: s.location_type != "CHILLER")
        floor = nn_then_2opt(entry, ambient, step_free)
        floor += nn_then_2opt(last(floor, entry), chilled, step_free)   # EC-33
        seq += floor
        cursor = seq[-1].node_id
    till = nearest_till(cursor, step_free)                    # FR-18
    nodes = stitch(start, seq, till)                          # shortest path between neighbours
    return MultiRoute(nodes=nodes, stops=seq, till=till, ...)
```

**Chilled stops come last within their own floor's pass**, not after every
floor. Appending them after all floors would send a shopper back upstairs
whenever a chiller sat above the ground floor, breaking FR-17's one pass per
floor. In the demo store every chiller is on floor 0 — the final pass — so
chilled items are still the last things picked before the tills.

A SKU held in several places takes the placement on a floor the basket already
visits, nearest the start, so a second placement never adds a floor.

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

## 11. The Streamlit interface

There is no HTTP layer (C-03). The page calls the compiled graph in the same
process, so what would have been a request contract is a function signature.

```python
# app.py — the whole surface between page and graph
GRAPH = build_graph()                      # @st.cache_resource, built once

def run_query(query: str, start_node: str, step_free: bool) -> JourneyState:
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    return GRAPH.invoke(initial_state(query, start_node, step_free), cfg)

def resume(choice: Choice) -> JourneyState:
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    return GRAPH.invoke(Command(resume=choice), cfg)

def plan_route(basket: list[BasketItem]) -> JourneyState:
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    return GRAPH.invoke({"basket": basket, "mode": "multi"}, cfg)
```

Three mechanics carry what the API used to:

| Was | Is |
|---|---|
| `POST /journey` | `run_query(...)` — returns **results only**, never a route |
| `POST /journey/resume` | `resume(choice)` on the next page run, same `thread_id` |
| `POST /route` | `plan_route(basket)` — a second graph run, from the basket |
| `GET /journey/{id}` | `GRAPH.get_state(cfg)` — the checkpoint is the record (EC-41) |
| SSE progress stream | `st.status` updated from the node names the graph yields |

**What the page holds and what it does not.** `st.session_state` holds exactly
two things: the `thread_id` and the basket draft. Everything else is read back
from the checkpoint, because Streamlit re-executes the script on every
interaction and local state would drift from graph state (EC-36, EC-41).

**Caching is load-bearing, not an optimisation.** The store, the BM25 index and
the distance and predecessor matrices are built in `@st.cache_resource`
builders in `ui/resources.py`. Without that, every click rebuilds ~314 nodes of
all-pairs Dijkstra and NFR-05's five seconds are gone before the search starts.

**The search box lives inside `st.form`**, so the graph is invoked on submit
rather than on each keystroke.

**Thread lifetime.** A `thread_id` is minted per search and swept after
`THREAD_TTL_MINUTES` (§14). LangGraph does not expire threads, so without the
sweep every abandoned clarification leaks a checkpoint (EC-34).

---

## 12. Error taxonomy

| Error | Raised when | Handling |
|---|---|---|
| `StoreDataError` | Startup validation fails | **Refuse to start.** Never serve a half-loaded store |
| `UnknownStoreError` | store_id not loaded | Refuse at startup; the page never offers a store that is not loaded |
| `InvalidNodeError` | start_node absent from the graph | The picker is built from the graph, so this is a bug, not shopper input. Fall back to the entrance and log |
| `UnreachableNodeError` | Predecessor matrix says NO_PATH | Log as a data bug. Should be impossible after §13 |
| `ModelUnavailableError` | Timeout, 429, 5xx, refusal stop reason | Caught in the node; deterministic fallback; append to `degraded` |
| `SchemaValidationError` | Structured output fails the model | Same. Rare with strict mode, but a truncated reply (`max_tokens` reached) still fails |
| `GroundingError` | Model named a SKU outside the candidate set | Never surfaced. Drop the suggestion, log loudly |
| `VerificationError` | `verify` found a claim that does not match the service result | Never surfaced as written. Discard the composed text, render the template, record the mismatch (EC-47) |

The split that matters: a **data** error stops the service, a **model** error
degrades one node. Nothing in the second class can produce a wrong location or a
wrong stock figure, because no model sits on those paths.

---

## 13. Startup validation

**The rules live in `schema.md` §7** — forty-three refusals numbered V-01 to V-74
with gaps between blocks, and five warnings, W-01 to W-05. They supersede the
eleven checks this section used to list. They are schema territory: what
makes a store folder well formed is a property of the format, not of this
application. What belongs here is *when* they run, in what order, and what
happens when one fails.

`validation.py` runs them inside the `@st.cache_resource` builder that loads the
store, which means they run **once per process, before the first search**, and a
failure raises rather than returning a half-loaded store.

| Phase | Checks | Why this order |
|---|---|---|
| 1 · Parse | Column presence, types, encodings | Nothing else can run against a file that will not parse |
| 2 · Within-file | Uniqueness, ranges, enum membership | Cheap, and catches most hand-authoring errors |
| 3 · Referential | Placement → SKU, placement → map node, stock → SKU | Needs every file loaded, so it cannot come earlier |
| 4 · Graph | Connectivity, positive weights, every floor reachable, lift-only subgraph connected | Needs the graph built, which needs phase 3 to have passed |
| 5 · Store shape | At least one checkout node, levels agree with the map | Last, because it is the only phase that encodes a requirement rather than a data rule |

Phase 4 is the one worth naming in a review: the lift-only subgraph is checked
for connectivity separately, because a store can be perfectly walkable and
still have no step-free path between two floors. FR-19 would then be
unsatisfiable at runtime, and the shopper would be the one to discover it.

A failure names the file, the row and the rule. `StoreDataError` is the only
error in §12 that refuses to start.

---

## 14. Configuration

```python
MIN_QUERY_CHARS     = 2       # EC-01
MAX_BATCH_TERMS     = 30      # EC-06
NL_WORD_THRESHOLD   = 4
BM25_K1, BM25_B     = 1.2, 0.5
SEARCH_LIMIT        = 10
FUZZY_THRESHOLD     = 75      # rapidfuzz ratio — set on the query set, Phase 4
FUZZY_TRIGGER_SCORE = 2.0     # BM25 below this triggers the fuzzy retry
SUGGESTION_THRESHOLD = 60     # nearest names offered when nothing matches — EC-03
AMBIGUITY_MIN_HITS  = 3
AMBIGUITY_MARGIN    = 0.15    # §8.4
MAX_CLARIFY_ROUNDS  = 2       # EC-35
THREAD_TTL_MINUTES  = 30      # EC-34 — abandoned interrupts
MODEL_TIMEOUT_S     = 6
ROUND_TOLERANCE_M   = 0.5     # §9 verify — rounding slack on a distance claim
NO_PATH             = -9999   # scipy sentinel
EPSILON             = 1e-9

# GroqCloud (C-06). Schema-bound calls need strict structured output, which
# only the gpt-oss models offer. Re-verify these IDs before Phase 6.
MODEL_UNDERSTAND    = "openai/gpt-oss-20b"
MODEL_SUBSTITUTE    = "openai/gpt-oss-120b"
MODEL_DESCRIBE      = "openai/gpt-oss-20b"
MODEL_MAX_TOKENS    = 1024    # per call; reasoning tokens count against it
MODEL_CALLS_PER_SESSION = 60  # public-deployment guard — then fallbacks only
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
| Integration · verify | §9 verify pass, EC-47 | A deliberately corrupted aisle, distance and availability each rejected; the template answer is rendered instead; `verified` is never true on a mismatch (AC-10) |
| Validation | §13 and `schema.md` §7 | One malformed fixture per phase, each expected to refuse startup with the file, row and rule named |

**The test that matters most** is the fallback suite. It is the only thing that
proves the claim the whole design rests on — that a model failure degrades
fluency and never correctness. Forcing each of the three model nodes to fail and
asserting the journey still returns a correct location and a correct route is
what turns that from an assertion into a fact.

---

## 16. Sequences

Lifelines throughout: Shopper · Page · Graph · Catalogue · Stock · Planogram ·
RouteEngine. Model calls and the verify gate are shown as activations on Graph,
because the node owns them.

### 16.1 Single product

```
Shopper   Page        Graph          Catalogue   Stock    Planogram  Routing
   │ "coke 500ml" · F0/A01 · submit (st.form)
   ├───────►│  run_query(q, start_node, step_free)
   │        ├──────────►│
   │        │           │ classify_query → shape="term"
   │        │           ├────────────────►│  search(term, filter, 10)
   │        │           │                 │ BM25 → candidates
   │        │           │                 ├────────►│ positions([candidates])
   │        │           │                 │◄────────┤ ranged + shelf_qty
   │        │           │                 │ rank: ranged → in stock →
   │        │           │                 │       variant → bm25 → popularity
   │        │           │◄────────────────┤  ranked candidates
   │        │           │ needs_clarification? (top−2nd)/top ≥ 0.15 → no
   │ ┌ opt [margin < 0.15] ──────────────────────────────────────────────────┐
   │ │      │◄──────────┤ interrupt({options})
   │ │◄─────┤ st.radio options
   │ ├─────►│ picks one      ═══ NEW PAGE RUN ═══
   │ │      ├──────────►│ resume(choice)
   │ └────────────────────────────────────────────────────────────────────────┘
   │        │           ├──────────────────────────►│ check_availability([sku])
   │        │           │◄──────────────────────────┤ shelf_qty 14 · ranged TRUE
   │        │           ├─────────────────────────────────────►│ for_skus([sku])
   │        │           │◄─────────────────────────────────────┤ F1-A07-R03·S02·HOME
   │        │           │ route_single — nearest of the placements
   │        │           ├──────────────────────────────────────────────►│
   │        │           │   distance(start, node) + path(start, node)
   │        │           │◄──────────────────────────────────────────────┤
   │        │           │   45.0 m · 12 hops · O(1) matrix read, no search
   │        │           │ ▓ describe_route [model · gpt-oss-20b]
   │        │           │ ▒ verify — 5 checks against service state → verified
   │        │◄──────────┤ JourneyState, verified=True
   │◄───────┤ result card + floor plate + directions
```

Three things this exists to show. Ranking calls **Stock before availability is
checked**, because `ranged` and `in stock` are ranking signals (FR-06), not just
output. The clarification is a **new page run**, not a continuation — Streamlit
holds no request open. And `verify` sits between the composed answer and the
page, so nothing unverified can render (NFR-02).

### 16.2 Multiple products

```
Shopper   Page        Graph          Catalogue   Stock    Planogram  Routing
   │ "milk, bread, eggs, chicken thighs" · F0/A01 · submit
   ├───────►│  run_query(...)
   │        ├──────────►│
   │        │           │ classify_query → shape="batch", 4 terms
   │ ┌ loop [per term, concurrent] ───────────────────────────────────────────┐
   │ │      │           ├────────────────►│ search(term, filter, 10)
   │ │      │           │                 ├────────►│ positions(…)
   │ │      │           │                 │◄────────┤
   │ │      │           │◄────────────────┤ ranked candidates
   │ └────────────────────────────────────────────────────────────────────────┘
   │        │           │ milk ✓ · eggs ✓ · chicken ✓ · bread → 12 near-equal
   │ ┌ opt [bread ambiguous] ─────────────────────────────────────────────────┐
   │ │      │◄──────────┤ interrupt({bread options})
   │ │◄─────┤           │
   │ ├─────►│ picks "Hovis Wholemeal 800g"   ═══ NEW PAGE RUN ═══
   │ │      ├──────────►│ resume(choice) — other three stay resolved
   │ └────────────────────────────────────────────────────────────────────────┘
   │        │           ├══════════════════════════►│ check_availability([4 SKUs])
   │        │           │◄══════════════════════════┤   ◄── ONE call, not four
   │        │           │ milk 14 · bread 6 · eggs 21 · chicken 0
   │ ┌ opt [any out of stock] ────────────────────────────────────────────────┐
   │ │      │           ├────────────────►│ by_category + dietary filter
   │ │      │           │◄────────────────┤ safe candidates only
   │ │      │           │ ▓ suggest_substitutes [model · gpt-oss-120b]
   │ │      │           │   reject any SKU outside the candidate set
   │ └────────────────────────────────────────────────────────────────────────┘
   │        │           ├═════════════════════════════════════►│ for_skus([4])
   │        │           │◄═════════════════════════════════════┤  ◄── ONE call
   │        │           │ after_locations — basket still empty → END
   │        │◄──────────┤ results ONLY. 3 available, 1 out of stock. NO ROUTE.
   │◄───────┤ grouped list, in-stock first + "Add 3 available to basket"
   │
   │ ╔═══ BASKET GATE — FR-21 to FR-24 ═══════════════════════════════════════╗
   │ ║ shopper adds the 3 available items, then asks to plan a route          ║
   │ ╚════════════════════════════════════════════════════════════════════════╝
   ├───────►│  ═══ NEW PAGE RUN ═══
   │        ├──────────►│ plan_route(basket)
   │        │           │ route_multi — group by floor, order F1 then F0,
   │        │           │               chilled deferred to the last pass
   │ ┌ loop [per floor, highest first] ───────────────────────────────────────┐
   │ │      │           ├──────────────────────────────────────────────►│
   │ │      │           │   nearest_core → nn_then_2opt over the matrix
   │ │      │           │◄──────────────────────────────────────────────┤
   │ └────────────────────────────────────────────────────────────────────────┘
   │        │           ├──────────────────────────────────────────────►│
   │        │           │   path(cursor, F0-TILL-01)
   │        │           │◄──────────────────────────────────────────────┤
   │        │           │   ordered node path · 2 floors · 68 m · ends at tills
   │        │           │ ▓ describe_route [model · gpt-oss-20b]
   │        │           │ ▒ verify — 5 checks → verified
   │        │◄──────────┤ route + directions
   │◄───────┤ route drawn across the floor plates, tabs F0 / F1
```

Legend: `▓` a model call, `▒` the verify gate, `═══►` a batched call.

Four things this exists to show:

1. **Two batched calls, not eight.** `check_availability` and `for_skus` each
   take a list. Against a real stock service that is one request instead of
   sixty, and designing the signature that way from the start avoids an N+1
   rewrite.
2. **The clarification keeps the resolved terms.** Only `bread` asks; milk, eggs
   and chicken stay resolved across the interrupt.
3. **The first run returns no route.** `after_locations` finds the basket empty
   and ends, so the basket gate is structural rather than a UI convention — a
   route is never planned to an empty shelf.
4. **Three page runs** for one journey — search, resume, route. Each is a fresh
   top-to-bottom execution reading state from the checkpoint.
