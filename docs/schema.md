# Data Schema

**Project:** Multi-Floor Store Product Finder and Navigation Agent
**Version:** 1
Companions: [requirements](https://claude.ai/artifact/3EX5yVGXaiUrGvMukseQbz) ·
[HLD](https://claude.ai/artifact/TA9jWLPoYuomMyMLDLuVYB) ·
[LLD](https://claude.ai/artifact/ErGjPov73E5kEch1APTEpf)

> **What this document is.** The six CSV files that describe one store: every
> column, every type, every referential rule, and the checks that run before the
> first search. It is the contract for onboarding a store. Rules cite the
> requirement or edge case they serve rather than restating it.

---

## 1. The store folder

One store is one folder, and **the folder name is the store identifier** — no
store ID is repeated on every row.

```
data/
  SBY-DEMO-001/          ← three-floor demo store
    store.csv
    products.csv
    stock.csv
    planogram.csv
    map_nodes.csv
    map_edges.csv
  SBY-PORT-002/          ← two-floor portability store (AC-09)
    …the same six files
```

### 1.1 Six files, four kinds of data

| File | Kind | Shape | Rows |
|---|---|---|---|
| `store.csv` | provenance | key–value | 5 |
| `products.csv` | catalogue | one row per SKU | ~180 |
| `stock.csv` | stock position | one row per SKU | ~180 |
| `planogram.csv` | planogram | one row per placement — **the join table** | ~250 |
| `map_nodes.csv` | store map | one row per walkable point | ~310 |
| `map_edges.csv` | store map | one row per path | ~350 |

The map is two files because a graph does not fit one table. `store.csv` holds
the three facts that belong to the store rather than to any row: the planogram
version, the stock extract time, and the statement that the data is synthetic
(C-04).

### 1.2 How they join

`planogram.csv` is the join table: `sku` into the catalogue, `node_id` into the
map. Three cardinalities carry meaning, and §6 enforces them:

- **`stock.csv` is total over `products.csv`.** Every SKU has a stock row. "We
  don't carry it" is said with `ranged=false`, never with a missing row.
- **`planogram.csv` is partial.** A SKU with no placement is legitimate — not
  ranged here (EC-04), or ranged with no recorded shelf (EC-19).
- **`planogram.csv` is many-to-one both ways.** One SKU may hold several
  placements (EC-20, the normal case) and one node holds many SKUs.

---

## 2. CSV conventions

Each one closes a failure mode CSV introduces.

### 2.1 File format

| Rule | Value | Why |
|---|---|---|
| Encoding | **UTF-8, no BOM** | Excel writes a BOM by default; it becomes part of the first column's name and the header check fails confusingly |
| Line ending | LF | Keeps the diff readable in a public repo |
| Quoting | RFC 4180 — double quotes, doubled to escape | Product names contain commas and apostrophes |
| Header | **Required, exact** | Unknown and missing columns are both refusals (V-01). A typo'd header otherwise silently drops a column |
| Column order | Not significant | Columns are read by name |
| Row order | Not significant | But files are **sorted by primary key** so a range change produces a small diff |
| Empty file | Refusal | A header with no rows is a refusal for every file except `planogram.csv` |
| Trailing blank line | Permitted, ignored | — |

### 2.2 The three-state boolean

**The single most important rule here.** A dietary flag has three states, and
CSV has no null, so the vocabulary is explicit and closed:

| Cell content | Means |
|---|---|
| `true` | True. Recorded, affirmative |
| `false` | False. **Recorded**, negative — someone checked |
| *(empty)* | **Unknown.** Nobody checked |

`TRUE`, `T`, `1`, `0`, `yes`, `NULL`, `N/A`, `-` and a cell of spaces are all
refusals (V-04). A loader that coerces is a loader that guesses.

**The trap.** `pandas.read_csv` reads an empty cell as `NaN`, which is falsy, so
`if product.diet_gluten_free:` silently means "not gluten free" for every
product nobody checked — the collapse NFR-03 forbids. Read these columns as
strings and map the three tokens explicitly. Never `dtype=bool`, never
`fillna(False)`.

**Every `diet_*` column is three-state.** `age_restricted`, `own_brand`,
`ranged`, `seasonal`, `bidirectional`, `step_free`, `trolley` and `is_open` are
**two-state and required** — an empty cell is a refusal. Those fields have no
unknown state.

### 2.3 List-valued columns

`synonyms` and `allergens_contains` are **pipe-delimited** (`|`) — a comma is
the field delimiter, and the quoting needed to escape it does not survive a
round trip through a spreadsheet.

```
coke|cola|coca cola
```

- Segments are trimmed of surrounding spaces; inner spaces are kept.
- No empty segments, no leading or trailing `|` (V-05).
- An empty cell is an empty list — **except for `allergens_contains`**, below.

**`allergens_contains` is three-state at list level** — §2.2's rule one level up:

| Cell content | Means |
|---|---|
| `milk\|soya` | Checked. Contains milk and soya |
| `none` | **Checked. Contains none of the declared allergens** |
| *(empty)* | **Unknown.** The declaration has not been recorded |

`none` is a value, not a convention: it says somebody looked and found nothing,
which is a different claim from an empty cell. It may not appear alongside
another allergen (V-22).

### 2.4 Columns that must be read as text

| Column | Risk |
|---|---|
| `sku` | A spreadsheet reads `7123456` as a number. Any SKU with a leading zero loses it, permanently and silently |
| `barcode` | EAN-13 is 13 digits. Excel renders it as `5.449E+12` and **saves it that way** |
| `node_id`, `edge_id`, `from_node`, `to_node` | Safe in practice (they start with a letter) but declared text for consistency |

**Format these columns as Text before typing in them.** A loader cannot detect
the damage afterwards — a lost leading zero leaves a valid-looking SKU. Hence
the convention that SKUs never begin with a zero.

### 2.5 Numbers and units

| Quantity | Type | Convention |
|---|---|---|
| Distance (`weight_m`, `penalty_m`) | float, metres | One decimal place. Metres throughout — **the only unit in the data** |
| Coordinates (`x_m`, `y_m`) | float, metres | One decimal. Per-store origin, **shared across floors** so the cores line up vertically |
| Counts (`shelf_qty`, `shelf_no`, `facing_from`, `facing_count`, `shelf_count`, `aisle`, `rack`) | int ≥ 0 | No thousands separators |
| `price_gbp` | decimal, 2 dp | **Display only.** Never summed, never compared. Pounds, no symbol |
| `popularity` | float, 0.0–1.0 | 2 dp. A ranking tiebreak, nothing else |
| Timestamp (`stock_as_of`) | ISO 8601, UTC, `Z` suffix | `2026-10-09T08:40:00Z` |
| Date (`planogram_version`) | ISO 8601 date | `2026-10-01` |

**Coordinates are presentational; distances are authoritative.** `x_m`/`y_m`
draw the floor plate (FR-20) and are never used to compute a distance — that
comes from `weight_m`. They may legitimately disagree, so W-03 warns rather than
refuses.

---

## 3. Identifier scheme

Every walkable point has an identifier that encodes where it is, so a wrong one
is visible by eye.

| Entity | Format | Example | Graph node? |
|---|---|---|---|
| Rack | `F{level}-A{aisle:02}-R{rack:02}` | `F1-A07-R03` | **yes** |
| Aisle end | `F{level}-A{aisle:02}-{N\|S}` | `F1-A07-N` | yes |
| Corridor junction | `F{level}-X{n:02}` | `F1-X04` | yes |
| Vertical core | `F{level}-CORE-{FRONT\|REAR}` | `F1-CORE-REAR` | yes |
| Service counter | `F{level}-CTR-{n:02}` | `F0-CTR-01` | yes |
| Assisted cabinet | `F{level}-CAB-{n:02}` | `F1-CAB-01` | yes |
| Dump bin | `F{level}-BIN-{n:02}` | `F0-BIN-01` | yes |
| Entrance | `F0-ENTRANCE` | — | yes |
| Checkout | `F0-TILL-{n:02}` | `F0-TILL-01` | yes |
| Shelf | `shelf_no` | `2` | **no** — a column on a placement |
| Facing | `facing_from` | `1` | **no** — a column on a placement |

Levels are integers from `0` and contiguous. Aisle and rack numbers appear
zero-padded in the identifier and unpadded in their own columns; V-50 checks
they agree. The identifier is for humans reading a diff, the columns are for the
code.

**The graph stops at rack level.** A shelf is not somewhere you walk, so it is a
column on a placement rather than a node. That keeps the map at roughly 310 rows
instead of 1,200 and still lets directions name a shelf:

```
F1 · A07 · R03   ·   S02 · P1
└── routable ──┘     └ columns ┘
   a graph node        spoken, not walked
```

**`counter`, `cabinet` and `bin` are new here.** The LLD could label a product
as being at a counter but had no node format to route to — and a deli counter is
not a rack, because it has no shelf and no facing.

---

## 4. File schemas

Legend for the **Req** column: **Y** required, non-empty · **N** optional, empty
permitted and meaningful · **3** three-state per §2.2.

### 4.1 `store.csv`

Two columns, `key` and `value`. The key set is closed — a missing or unknown key
is a refusal (V-10).

| `key` | `value` | Example |
|---|---|---|
| `store_id` | text, must equal the folder name | `SBY-DEMO-001` |
| `store_name` | text, shown in the UI | `Sainsbury's Demo Superstore` |
| `data_provenance` | `synthetic` — the only accepted value | `synthetic` |
| `planogram_version` | ISO date; bumped by a range change | `2026-10-01` |
| `stock_as_of` | ISO 8601 UTC timestamp | `2026-10-09T08:40:00Z` |

`data_provenance` makes C-04's synthetic-data statement a property of the data,
so the banner cannot be lost by forgetting to hard-code it.

**Not here:** `min_level` and `max_level`, derived from `map_nodes.level`, and
the start node, which is the sole `entrance`. Deriving them removes a chance for
the map and its description to disagree.

### 4.2 `products.csv`

One row per SKU. The catalogue — what the store *could* sell, independent of
this branch.

| Column | Type | Req | Constraint / note |
|---|---|---|---|
| `sku` | text | Y | **PK.** 7 digits, no leading zero (§2.4) |
| `name` | text | Y | Display name. Feeds the search index |
| `brand` | text | Y | `Own Brand` for own-label lines |
| `size` | text | Y | `500ml`, `1.5l`, `6 pack`. Parsed for variant match |
| `barcode` | text | N | EAN-13, exactly 13 digits when present |
| `department` | text | Y | Top-level grouping, e.g. `Drinks` |
| `aisle_category` | text | Y | Drives category queries (EC-09) and substitute candidacy (FR-09) |
| `synonyms` | list | N | Pipe-delimited. `coke\|cola` |
| `diet_gluten_free` | bool | 3 | — |
| `diet_vegan` | bool | 3 | — |
| `diet_vegetarian` | bool | 3 | — |
| `diet_halal` | bool | 3 | — |
| `allergens_contains` | list | 3 | Pipe-delimited, or `none`, or empty. §2.3 |
| `age_restricted` | bool | Y | Two-state. Drives the colleague-required outcome (OQ-07) |
| `price_gbp` | decimal | Y | 2 dp, display only |
| `own_brand` | bool | Y | Two-state. Ranking tiebreak |
| `popularity` | float | Y | 0.0–1.0, 2 dp. Ranking tiebreak |

`department` and `aisle_category` are free text, not enumerations: a new store
brings its own category names and FR-25 forbids a code change for that.

### 4.3 `stock.csv`

One row per SKU, total over `products.csv`. The branch position.

| Column | Type | Req | Constraint / note |
|---|---|---|---|
| `sku` | text | Y | **PK and FK** → `products.sku` |
| `ranged` | bool | Y | Two-state. Carried by *this* branch |
| `shelf_qty` | int | Y | ≥ 0 |

**`ranged` is load-bearing.** `ranged=false` and `shelf_qty=0` are different
answers to a shopper — "we don't carry it here" against "we carry it and it's
sold out" — and FR-08 requires the distinction. `ranged=false` with
`shelf_qty>0` is contradictory and refused (V-31).

**There is no "quantity unknown".** EC-18 is a runtime condition, not a data
state; an empty `shelf_qty` is a refusal. This is the one column where a guess
sends a shopper to an empty shelf.

### 4.4 `planogram.csv`

One row per placement. **The join table** — `sku` into the catalogue, `node_id`
into the map.

| Column | Type | Req | Constraint / note |
|---|---|---|---|
| `sku` | text | Y | FK → `products.sku` |
| `node_id` | text | Y | FK → `map_nodes.node_id` |
| `location_type` | enum | Y | Table below |
| `shelf_no` | int | N | 1 = top. Required for shelved types, forbidden otherwise |
| `facing_from` | int | N | 1 = leftmost. Same rule as `shelf_no` |
| `facing_count` | int | N | ≥ 1. Same rule as `shelf_no` |
| `seasonal` | bool | Y | Two-state. Suppressed at zero stock (EC-24) |

**PK is the composite `(sku, node_id, shelf_no, facing_from)`** — a SKU can
appear twice on one rack at different shelves, so `(sku, node_id)` is not
unique. There is no surrogate key, because nothing references a placement.

#### `location_type`

| Value | Meaning | Routable | Edge case |
|---|---|---|---|
| `HOME` | Primary planogram position | yes | — |
| `PROMO_ENDCAP` | Promotional end cap | yes | EC-20 |
| `SEASONAL` | Seasonal gondola | yes, suppressed at zero stock | EC-24 |
| `DUMP_BIN` | Front-of-store bin | yes | — |
| `CHILLER` | Chilled or frozen unit | yes, deferred to the last floor pass | EC-33 |
| `ASSISTED` | Locked cabinet — spirits, formula, blades | route to the cabinet, colleague required | EC-22 |
| `COUNTER` | Deli, fish, pharmacy | route to the counter, no shelf or facing | EC-23 |

#### Compatibility with the target node (V-46)

`location_type` constrains the kind of node a placement may point at and whether
the shelf columns are set. This is what stops a deli counter acquiring a shelf
number.

| `location_type` | Permitted `node_type` | `shelf_no` · `facing_from` · `facing_count` |
|---|---|---|
| `HOME` | `rack` | **required** |
| `CHILLER` | `rack` | **required** |
| `SEASONAL` | `rack`, `bin` | required on `rack`, forbidden on `bin` |
| `PROMO_ENDCAP` | `aisle_end` | **forbidden** |
| `DUMP_BIN` | `bin` | **forbidden** |
| `ASSISTED` | `cabinet` | **forbidden** |
| `COUNTER` | `counter` | **forbidden** |

"Forbidden" means the cell is empty.

### 4.5 `map_nodes.csv`

One row per walkable point.

| Column | Type | Req | Constraint / note |
|---|---|---|---|
| `node_id` | text | Y | **PK.** Format per §3, consistent with `node_type` |
| `node_type` | enum | Y | `rack` · `aisle_end` · `junction` · `core` · `counter` · `cabinet` · `bin` · `entrance` · `till` |
| `level` | int | Y | ≥ 0, contiguous across the store |
| `floor_name` | text | N | Repeated per level; must agree (V-51) |
| `aisle` | int | N | Required for `rack` and `aisle_end`; optional on `counter`, `cabinet` and `bin`; empty otherwise |
| `rack` | int | N | Required for `rack`, else empty |
| `shelf_count` | int | N | Required for `rack`, ≥ 1, else empty. Bounds `shelf_no` and lets "eye level" be derived |
| `zone` | text | N | A label, not an entity — see below |
| `x_m` | float | Y | Presentational (§2.5) |
| `y_m` | float | Y | Presentational (§2.5) |
| `is_open` | bool | Y | Two-state. `false` removes the node and its edges before the matrices are built (EC-32) |

Three columns need a word.

- **`floor_name`** repeats on every node of a level. An author fills it down;
  V-51 refuses a store where two nodes on one level disagree.
- **`shelf_count`** bounds `shelf_no` and lets "eye level" be derived — shelf 2
  of 3 is eye level, shelf 2 of 6 is not.
- **`zone`** is a label with nothing hanging off it. Closures are per-node via
  `is_open`, which is more capable than closing whole zones and needs no zone
  table.

### 4.6 `map_edges.csv`

One row per path between two nodes. The row is **undirected or directed
according to `bidirectional`**; the loader expands it into the directed graph.

| Column | Type | Req | Constraint / note |
|---|---|---|---|
| `edge_id` | text | Y | **PK.** `E{n:04}`, e.g. `E0137` |
| `from_node` | text | Y | FK → `map_nodes.node_id` |
| `to_node` | text | Y | FK → `map_nodes.node_id`, ≠ `from_node` |
| `kind` | enum | Y | `aisle` · `corridor` · `lift` · `escalator` · `stairs`. The demo store uses no `escalator` — FR-14 commits to stairs and lifts — but the format accepts one, because FR-25 means another store may have them |
| `weight_m` | float | Y | **> 0.** Walking distance in metres |
| `penalty_m` | float | Y | ≥ 0. Wait cost as its walking equivalent |
| `bidirectional` | bool | Y | Two-state. `false` = `from_node` → `to_node` only |
| `step_free` | bool | Y | Two-state. `false` for `escalator` and `stairs` (V-62) |
| `trolley` | bool | Y | Two-state. `false` for `stairs` (V-62) |
| `is_open` | bool | Y | Two-state. `false` removes the edge (EC-30) |

Four rules the loader must follow.

- **Effective weight is `weight_m + penalty_m`.** The only arithmetic done to an
  edge.
- **The lift penalty is in metres**, not seconds: a 30-second wait becomes its
  walking equivalent, so the matrix stays in one unit. It is also the tuning
  knob for floor-bouncing — raise it and the router clusters harder by floor.
- **Parallel edges collapse to the minimum effective weight.** The rear core
  carries both a lift and stairs between the same pair of nodes, so
  `(from_node, to_node)` is not unique — which is why `edge_id` exists. **For
  the step-free matrix, filter to `step_free=true` first and then take the
  minimum**, or the stairs' lower weight hides the lift. The wrong order gives a
  step-free matrix quietly identical to the full one.
- **A vertical edge joins two `core` nodes at the same core position on
  different levels** (V-63). Non-adjacent levels are allowed — an express lift
  is real — but a connector arriving at a different core is two connectors.

---

## 5. Worked example — one SKU across all six files

Coca-Cola Classic 500ml, on its home rack in the drinks aisle on floor 1 and on
a promotional end cap at the same aisle's north end.

```csv
# store.csv
key,value
store_id,SBY-DEMO-001
store_name,Sainsbury's Demo Superstore
data_provenance,synthetic
planogram_version,2026-10-01
stock_as_of,2026-10-09T08:40:00Z

# products.csv
sku,name,brand,size,barcode,department,aisle_category,synonyms,diet_gluten_free,diet_vegan,diet_vegetarian,diet_halal,allergens_contains,age_restricted,price_gbp,own_brand,popularity
7123456,Coca-Cola Classic,Coca-Cola,500ml,5449000000996,Drinks,Soft Drinks,coke|cola,true,true,true,,none,false,1.65,false,0.82

# stock.csv
sku,ranged,shelf_qty
7123456,true,14

# planogram.csv
sku,node_id,location_type,shelf_no,facing_from,facing_count,seasonal
7123456,F1-A07-R03,HOME,2,1,3,false
7123456,F1-A07-N,PROMO_ENDCAP,,,,false

# map_nodes.csv
node_id,node_type,level,floor_name,aisle,rack,shelf_count,zone,x_m,y_m,is_open
F1-A07-R03,rack,1,Ambient Grocery,7,3,5,Drinks,42.0,18.0,true
F1-A07-N,aisle_end,1,Ambient Grocery,7,,,Drinks,42.0,2.0,true

# map_edges.csv
edge_id,from_node,to_node,kind,weight_m,penalty_m,bidirectional,step_free,trolley,is_open
E0412,F1-A07-R03,F1-A07-R02,aisle,3.2,0.0,true,true,true,true
E0413,F1-A07-R03,F1-A07-R04,aisle,3.2,0.0,true,true,true,true
E0137,F0-CORE-REAR,F1-CORE-REAR,lift,6.0,25.0,true,true,true,true
E0139,F0-CORE-REAR,F1-CORE-REAR,stairs,11.0,0.0,true,false,false,true
```

Four things to read off it. `diet_halal` is **empty** — unknown, not false, so a
halal requirement will not be satisfied (NFR-03). `allergens_contains` is
`none` — checked and empty, a stronger claim than the blank cell above it. The
end-cap placement leaves the three shelf columns empty, because an end cap has
no shelf (V-46). And `E0137` and `E0139` are parallel rows on one pair of
nodes — the lift and the stairs — which is why `edge_id` exists and why the
loader takes a minimum.

---

## 6. Referential integrity

| # | Relationship | Cardinality | Total? | Violation |
|---|---|---|---|---|
| R-1 | `stock.sku` → `products.sku` | 1:1 | **Yes, both ways** | Refuse (V-30, V-32) |
| R-2 | `planogram.sku` → `products.sku` | N:1 | No | Refuse on orphan (V-40) |
| R-3 | `planogram.node_id` → `map_nodes.node_id` | N:1 | No | Refuse on orphan (V-41) |
| R-4 | `map_edges.from_node` → `map_nodes.node_id` | N:1 | No | Refuse (V-60) |
| R-5 | `map_edges.to_node` → `map_nodes.node_id` | N:1 | No | Refuse (V-60) |
| R-6 | `store.store_id` → folder name | 1:1 | Yes | Refuse (V-11) |

R-1 is total in **both** directions and it is the only one that is: every
product has exactly one stock row and every stock row has a product. A SKU in
the stock file but not the catalogue is a stale extract; a SKU in the catalogue
with no stock row has no answer to FR-07.

R-2 and R-3 are deliberately partial, and the gap carries meaning —
`products` ⟶ no placement is EC-19 or EC-04, and a `map_nodes` row with no
placement is most of the map.

---

## 7. Validation

Run once when the store folder is loaded, before the first query is served.
**Invalid data stops the load** — NFR-07, and AC-14 requires each refusal to
name the fault. A data error is not a request-time edge case; a half-loaded
store is never served.

IDs are stable and gaps between blocks are intentional, so a new rule does not
renumber the ones a test references.

### 7.1 Refusals — format

| ID | Check | Catches |
|---|---|---|
| V-01 | Header matches the schema exactly: no missing, no unknown, no duplicate column | A typo'd header silently dropping a column |
| V-02 | UTF-8 decodes, no BOM | A store folder round-tripped through Excel |
| V-03 | No duplicate primary key, in any file | **New with CSV.** A JSON object could not hold one key twice; two rows can. Named in requirements §7 |
| V-04 | Every boolean cell is `true`, `false`, or — for `diet_*` and `allergens_contains` only — empty | `TRUE`, `1`, `yes`, `N/A` being coerced to a guess |
| V-05 | Pipe-delimited cells have no empty segments and no leading or trailing `\|` | `coke\|\|cola`, a trailing delimiter |
| V-06 | Every required cell is non-empty; every forbidden cell is empty | — |
| V-07 | Every typed cell parses as its type — integers, decimals, ISO dates and timestamps; `node_type` and `kind` take a listed value; `edge_id` matches `E{n:04}` | `14 units` in `shelf_qty`; a misspelt node type silently matching no rule |

### 7.2 Refusals — `store.csv`

| ID | Check | Catches |
|---|---|---|
| V-10 | Exactly the five keys of §4.1, no more, no fewer | A typo'd key being read as a missing one |
| V-11 | `store_id` equals the folder name | A folder copied and half-renamed |
| V-12 | `data_provenance` is `synthetic`; `planogram_version` and `stock_as_of` parse as ISO 8601 | C-04 being lost in onboarding |

### 7.3 Refusals — `products.csv`

| ID | Check | Catches |
|---|---|---|
| V-20 | `sku` is 7 digits and does not begin with `0` | §2.4's unrecoverable coercion |
| V-21 | `barcode`, when present, is exactly 13 digits and unique across the file | Scientific-notation damage; EC-10 |
| V-22 | `allergens_contains` does not combine `none` with a named allergen | A contradictory declaration reaching NFR-03 |
| V-23 | `price_gbp` ≥ 0 with at most 2 dp; `popularity` in 0.0–1.0 | — |

### 7.4 Refusals — `stock.csv`

| ID | Check | Catches |
|---|---|---|
| V-30 | Every `sku` exists in `products.csv` | A stale stock extract (LLD §13 check 8) |
| V-31 | Not (`ranged=false` and `shelf_qty>0`) | §4.3's unmodelled run-out state |
| V-32 | Every `products.sku` has a stock row; row counts are equal | A missing row being read as "not carried" |
| V-33 | `shelf_qty` ≥ 0 | — |

### 7.5 Refusals — `planogram.csv`

| ID | Check | Catches |
|---|---|---|
| V-40 | Every `sku` exists in `products.csv` | EC-43 (LLD §13 check 7) |
| V-41 | Every `node_id` exists in `map_nodes.csv` | EC-21 (LLD §13 check 6) |
| V-42 | `location_type` is one of the seven values | — |
| V-43 | `shelf_no` ≤ the target node's `shelf_count` | A shelf that is not on the rack |
| V-44 | `facing_from` ≥ 1 and `facing_count` ≥ 1 | — |
| V-45 | No two placements on the same `(node_id, shelf_no)` overlap in facings | Two products claiming the same frontage |
| V-46 | `location_type` and the target `node_type`, and the shelf columns, satisfy §4.4's matrix | A counter with a shelf number (supersedes LLD §13 check 11) |

### 7.6 Refusals — `map_nodes.csv`

| ID | Check | Catches |
|---|---|---|
| V-50 | `node_id` matches the §3 format for its `node_type`, and its embedded level, aisle and rack agree with the columns | `F1-A07-R03` on a row that says level 2 |
| V-51 | All nodes on one `level` carry the same `floor_name` | §4.5's denormalisation drifting |
| V-52 | `level` values are contiguous from 0 | A store missing a floor plate |
| V-53 | Exactly one `entrance` node, and it is on level 0 | An ambiguous or absent default start point (FR-15) |
| V-54 | At least one `till` node, on level 0 | FR-18 with no terminus (LLD §13 check 9) |
| V-55 | `shelf_count` ≥ 1 on every `rack`, empty on every other type | An unbounded `shelf_no` |
| V-56 | No two nodes share `(level, x_m, y_m)` | Two points drawn on top of each other |

### 7.7 Refusals — `map_edges.csv`

| ID | Check | Catches |
|---|---|---|
| V-60 | Both endpoints exist in `map_nodes.csv` | A typo in a hand-authored map (LLD §13 check 1) |
| V-61 | `weight_m` > 0 and `penalty_m` ≥ 0 | EC-45 — a non-positive weight breaks Dijkstra's guarantee outright (LLD §13 check 2) |
| V-62 | `step_free=false` for `escalator` and `stairs`; `trolley=false` for `stairs` | A step-free route sending a wheelchair up an escalator |
| V-63 | A `lift`, `escalator` or `stairs` edge joins two `core` nodes at the same core position on different levels; an `aisle` or `corridor` edge joins two nodes on the same level | A connector that arrives in the wrong half of the building; a corridor through a ceiling |
| V-64 | `from_node` ≠ `to_node` | A self-loop |
| V-65 | No two rows share `(from_node, to_node, kind)` | Two indistinguishable connectors, where EC-30 could not say which to disable |

### 7.8 Refusals — the assembled graph

Run after the open nodes and edges are expanded into the directed graph.

| ID | Check | Catches |
|---|---|---|
| V-70 | Strongly connected over all levels | EC-44, EC-29 — a store you cannot walk across (LLD §13 check 3) |
| V-71 | Every level reachable from the `entrance` node | A floor with no working core (LLD §13 check 4) |
| V-72 | The `step_free=true` subgraph is also strongly connected | EC-31 — step-free routing that silently has no answer (LLD §13 check 5) |
| V-73 | Every node with a placement is reachable from the `entrance` | A product on an orphaned rack |
| V-74 | Every `till` node reachable from every level | FR-18 unsatisfiable from upstairs |

V-70 and V-72 run **after** `is_open=false` rows are removed, because that is
the graph the matrices are built from.

### 7.9 Warnings

These load the store and log. Each is suspicious but has a defined meaning, so
refusing would block a legitimate case.

| ID | Warning | Why not a refusal |
|---|---|---|
| W-01 | An `aisle_category` whose products sit on racks in more than one aisle | Legitimate for a category split across an aisle boundary, but usually a typo in one row |
| W-02 | A SKU with `ranged=true` and `shelf_qty>0` but no placement | EC-19 explicitly handles it — availability is shown and the location reads as unknown |
| W-03 | An `aisle` or `corridor` edge whose `weight_m` differs from the straight-line distance between its endpoints' coordinates by more than 50% | Legitimate for a dogleg; a large disagreement is usually a mistyped weight (§2.5) |
| W-04 | A node of type `rack` with no placements on it | An empty rack is real; a floor of them means the planogram was not finished |
| W-05 | A `diet_*` column empty for more than half the catalogue | Honest unknown, but it makes dietary filtering useless, and silently so |

The line between the tiers: a missing *stock* row has no meaning, so it is
refused. A missing *placement* has a meaning the system already handles, so it
warns.

---

## 8. Sizing

**The catalogue and the stock position do not grow with floor count** — the same
~180 products sit somewhere, so only the map changes shape. That is what makes a
three-floor demo nearly free.

| File | Demo — 3 floors | Portability — 2 floors |
|---|---|---|
| `store.csv` | 5 | 5 |
| `products.csv` | 180 | 180 |
| `stock.csv` | 180 | 180 |
| `planogram.csv` | ~250 | ~250 |
| `map_nodes.csv` | **314** | **143** |
| `map_edges.csv` | **352 rows → 704 arcs** | **160 rows → 320 arcs** |

Where the 314 nodes come from:

| Term | Count | From |
|---|---|---|
| Racks | 216 | 36 aisles × 6 racks — F0 12, F1 14, F2 10 |
| Aisle ends | 72 | 36 aisles × 2 (N, S) |
| Corridor junctions | 6 | 2 per floor, where a corridor meets a core |
| Cores | 6 | 2 cores × 3 levels |
| Tills | 6 | authoring choice |
| Counters | 3 | deli, fish, bakery — all F0 |
| Cabinets | 2 | spirits F1, baby formula F2 |
| Dump bins | 2 | F0 and F1 front-of-store |
| Entrance | 1 | — |
| **Total** | **314** | |

Edge rows: 180 rack-to-rack (5 per aisle × 36) + 72 rack-to-aisle-end +
66 corridor segments between adjacent aisle ends + 12 junction links +
8 vertical (2 lifts × 2 spans, 2 stairs × 2 spans — no escalators, FR-14)
+ 1 entrance + 6 till + 7 counter, cabinet and bin links = **352 rows**.
Every row in the demo store is bidirectional, so expanding each into two arcs
gives **704 directed arcs**.

The aisle, rack and till counts are **authoring choices**, not derived facts.
Changing them touches only the two map files and the `node_id` values in
`planogram.csv` — which is what FR-25 and AC-09 test.

---

## 9. What the schema deliberately does not carry

| Not here | Why |
|---|---|
| **Shelf and facing nodes** | A shelf is not somewhere you walk. Columns on a placement, not rows in the map (§3) |
| **`min_level` / `max_level`** | Derived from `map_nodes.level`. A stored copy is a stored chance to disagree |
| **A zone table** | `zone` is a label; closures are per-node via `is_open` (§4.5) |
| **A surrogate placement key** | Nothing references a placement (§4.4) |
| **Product images, descriptions, nutrition panels** | Nothing in the requirements reads them, and supplier-supplied text is an untrusted input (EC-11) |
| **Price history, promotions, loyalty prices** | Out of scope. `price_gbp` is display only |
| **Any real retailer identifier, EAN range or store code** | The data is synthetic (C-04) and the repository is public |
| **Any shopper or colleague data** | No PII reaches a file in a public repository. Baskets and threads are runtime state |
| **Timestamps per stock position** | A-01 does not model staleness. One `stock_as_of` for the extract (§4.1) |
| **A "quantity unknown" encoding** | EC-18 is a runtime condition, not a data state (§4.3) |
