# Architecture

Rendered diagrams: **https://claude.ai/artifact/9rDaEZH2uFA1sLQhWTGH7C**
(private — share from the page's Share menu before sending it to anyone else)

This document is the written form of that page: the layer stack, the LangGraph
graph specification, the multi-floor store model, and the reasoning behind each
decision.

## Confirmed requirements

| Requirement | Decision |
|---|---|
| Store map source | Authored by us — no public multi-floor rack-level planogram exists |
| Store shape | 3 floors, ~12–14 aisles per floor, ~6 racks per aisle |
| User position | Shopper manually selects floor + aisle |
| Availability | Treated as live and correct (granted as an assumption) |
| Single product | Shortest path |
| Multiple products | Optimal shopping route (sequencing) |
| Floor order | Fixed, one picking pass per floor |
| Route terminus | Ground-floor checkout |
| Framework | LangGraph |

## 1. Layer stack

```
BROWSER        search · floor+aisle picker · single/multi toggle · basket
               multi-floor SVG map, floor switcher, route overlay
   │ POST /journey  ·  SSE node events ↩
FASTAPI        thin: validates input, owns thread_id, streams graph progress
   │ invoke(state, thread_id)
LANGGRAPH      9 nodes · 3 conditional edges · 1 cycle · 1 interrupt
               typed state, checkpointed per shopping session
   │ plain function calls — no model
SERVICES       catalogue · planogram · stock · routing (matrix + TSP)
   │
DATA           store_graph · planogram · products · stock  (JSON, in memory)
```

The load-bearing property: **the orchestrator holds no facts.** Gen AI lives
inside the LangGraph layer; locations, stock and distances are read from the
service layer on every request. Remove the model and the system still answers —
less fluently, but never wrongly.

## 2. The LangGraph graph

### State

```python
class JourneyState(TypedDict):
    # input
    raw_query: str
    mode: Literal["single", "multi"]
    start_node: str                      # from the floor+aisle picker

    # working
    parsed_query: ParsedQuery | None
    candidates: list[Product]
    basket: list[str]                    # SKUs
    availability: dict[str, Stock]
    locations: dict[str, list[Location]] # one SKU → many locations
    substitutions: dict[str, list[Product]]

    # output
    route: Route | None
    directions: list[str]
```

### Nodes

Nine nodes. **Six are plain Python functions, three call a model, one pauses
for the shopper.** That ratio is the design.

| Node | Kind | Does |
|---|---|---|
| `understand_query` | model — Haiku 5.5, structured output | NL query → typed catalogue filter |
| `search_catalogue` | deterministic | filter → real SKUs |
| `clarify` | `interrupt()` | ambiguous query → ask, wait, resume |
| `check_availability` | deterministic | stock lookup |
| `suggest_substitutes` | model — Opus 5.5 | out of stock → alternatives, dietary-filtered first |
| `resolve_locations` | deterministic | planogram → floor / aisle / rack / shelf |
| `route_single` | deterministic | matrix lookup, O(1) |
| `route_multi` | deterministic | floor-clustered sequencing |
| `describe_route` | model — Haiku 5.5 | node list → human directions |

### Edges

```
START → understand_query → search_catalogue
search_catalogue ─ ambiguous ──→ clarify ──resume──→ search_catalogue   (cycle)
                 ─ not ranged ─→ END
                 ─ matched ────→ check_availability
check_availability ─ out of stock ─→ suggest_substitutes ─→ resolve_locations
                   ─ all available ───────────────────────→ resolve_locations
resolve_locations ─ mode=single ─→ route_single ─┐
                  ─ mode=multi ──→ route_multi  ─┴→ describe_route → END
```

Three things here genuinely need a graph rather than a chain:

1. **The `clarify` cycle.** An ambiguous query goes back to search after the
   shopper answers. A linear chain cannot express this.
2. **The `mode` branch.** Read from state, not decided by a model.
3. **The early exit** for a product the store does not range.

### Checkpointing

`thread_id` = the shopping session. The basket survives across requests, and
the shopper can add items and resume. `InMemorySaver` for the POC; swap to a
SQLite checkpointer if the session needs to survive a restart.

## 3. Store model

### Synthetic layout

| Floor | Zone | Aisles |
|---|---|---|
| 2 | Non-food — health & beauty, household, baby, homeware | ~10 |
| 1 | Ambient grocery — tins, pasta, cereals, snacks, drinks, world foods | ~14 |
| 0 | Fresh & tills — produce, bakery, meat & fish, chilled, dairy | ~12 |

~6 racks per aisle gives roughly 216 rack nodes, plus corridors and vertical
connectors — around 300 nodes in total. Enough to read as a real store, small
enough to author by hand in a day.

### Location granularity

```
Floor → Zone → Aisle → Rack → Shelf → Facing
```

Rack is a first-class level rather than a detail inside an aisle, because that
is the granularity asked for. The planogram world calls this a *bay*; the data
model uses "rack" so the vocabulary matches the conversation.

**One SKU maps to several locations** — its home rack plus promotional end caps
— so the lookup returns a list and the router picks the nearest member.

### Vertical connectors

Two cores:

| Core | Contains | Position |
|---|---|---|
| Front | Lift | Near the entrance / tills |
| Rear | Lift + escalator | Back of the building |

Connectors are **weighted graph edges**, which is what makes the router avoid
pointless floor changes. The lift is tagged step-free and trolley-friendly, so
accessibility routing comes almost free: filter the graph to lift-only edges
and recompute.

Node vocabulary borrows OSM Simple Indoor Tagging — `level`, `min_level` /
`max_level`, connectors spanning a level range — so the authored map matches a
recognised indoor standard rather than inventing a private scheme.

## 4. Routing

### Precompute, don't search

The layout is static, so **all-pairs shortest paths across all three floors are
computed once at startup** (one `scipy.sparse.csgraph.shortest_path` call) and
cached. At ~300 nodes this is instant, and every single-product query becomes an
O(1) table lookup. No runtime graph search, and no need for A* — a heuristic
only pays off on large search spaces.

Because the matrix already spans floors, "which core should I use" falls out of
it rather than needing separate logic.

### Single product

Selected aisle node → product rack node. One matrix read.

### Multiple products — sequencing, not pathfinding

The shortest paths are already in the matrix. What remains is a travelling
salesman problem:

1. **Group items by floor.**
2. **Order floors: ride to the highest floor holding items, then work down,
   finishing at the ground-floor tills.**
3. **Within each floor**, nearest-neighbour construction then 2-opt over the
   precomputed distances. Milliseconds for any realistic basket.
4. **Stitch floors** through whichever core the matrix says is cheapest.

Because a SKU can sit in several locations this is strictly a *generalised* TSP
— pick one node per item group. Nearest-neighbour handles it naturally by
taking the closest member of each group.

### Why the floor order is fixed

A distance-only optimiser will send a shopper up and down repeatedly, because
it has no notion that a floor change is worse than the metres it costs.
Constraining to one picking pass per floor is better on three counts: it is what
a shopper expects, it shrinks the search space, and revisiting a floor almost
never repays the metres saved. It is also explainable — "we work floor by
floor" is a sentence a stakeholder understands; "we ran a TSP" is not.

**Transit is not a picking pass.** A shopper starting at the ground-floor
entrance crosses Floor 0 to reach the lift, rides to Floor 2, and picks Floor 0
on the way back down. One *pick* pass per floor still holds.

**Alternating cores removes the backtrack.** Enter a floor at one core, traverse
it, leave by the other. The shopper never walks back the way they came.

### Route terminus

The route ends at the tills, so it is a **closed path**, not an open one. That
also makes deferring chilled and frozen items to the final floor natural rather
than bolted on.

## 5. Gen AI placement

Three nodes call a model. **None is on the wire that returns a location, a
distance or a stock figure.** A hallucinated rack number sends a shopper to the
wrong floor, so the model is architecturally unable to produce one.

- `understand_query` — Haiku 5.5, one structured-output call. High volume, low
  complexity, latency-critical. Keyword search stays wired as the fallback.
- `suggest_substitutes` — Opus 5.5. Needs real reasoning over constraints.
- `describe_route` — Haiku 5.5. Pre-generate and cache per node pair where
  possible; the phrasing for a given pair does not change between shoppers.

**Allergens are the hard line.** Substitution candidates are filtered on
structured dietary attributes *before* the model sees them, so it chooses among
already-safe options rather than judging safety. Nothing generated asserts that
a product is gluten free, nut free, vegan or halal — that claim comes from a
catalogue attribute, passed through verbatim.

## 6. Where LangGraph would be theatre

Worth stating, because knowing where not to use it is what makes the rest
credible.

- **An LLM node that computes or chooses routes.** Routing is exact; keep it
  deterministic.
- **A ReAct agent deciding which tool to call.** The sequence is known — use
  explicit edges. An agent here adds latency, cost and nondeterminism to a
  problem with a known answer.
- **An LLM at every node "for consistency".** Six nodes have no business
  calling a model.

## 7. Known traps

Both bite the standard tutorial idiom.

**Do not pass `temperature=0`.** Nearly every LangChain example does. Sampling
parameters are rejected on the current Claude models — Opus 5.5 removes them
outright, Haiku 5.5 rejects non-default values. Construct the chat model
without it.

**Structured output and thinking interact badly.** Thinking is on by default
(adaptive) on the 5-family models, and there is a known failure where
`with_structured_output` raises a parse error with it enabled. Test that path on
day one, and consider `method="json_schema"` over the default
`"function_calling"`. Use `pydantic.BaseModel` (v2) — older examples import
`langchain_core.pydantic_v1`, which is wrong now.

**Pin versions.** The checkpointer is exported as both `MemorySaver` and
`InMemorySaver` depending on release, and the pause API moved from
`interrupt_before` to `interrupt()`. Check what your installed version exports
rather than trusting a blog post.

## 8. Data sources

No public dataset holds a real multi-floor supermarket planogram at rack level
— shelf layout is competitive information and retailers do not publish it. The
store map is therefore authored, which is the right answer anyway: no real
planogram would match a brief asking for three floors and racks.

| Source | Supplies | Caveat |
|---|---|---|
| [Open Food Facts](https://world.openfoodfacts.org/data) | Real products — names, brands, EAN-13 barcodes, categories, allergens. Bulk CSV/SQLite, ODbL | Coverage strongest in Western Europe; any field can be absent, allergens included |
| [Instacart Market Basket](https://www.kaggle.com/c/instacart-market-basket-analysis) | A real grocery taxonomy: 134 aisles, 21 departments, ~50k products mapped to both | 2017 competition data, research-use licence |
| [OSM Simple Indoor Tagging](https://wiki.openstreetmap.org/wiki/Simple_Indoor_Tagging) | Vocabulary for multi-floor indoor data | A schema, not a floor plan |
