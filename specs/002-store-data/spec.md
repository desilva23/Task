# Feature Specification: Synthetic Store Generator and Store Validator (Phase 1)

**Feature Branch**: none — work stays on `claude/planogram-store-navigation-czn7bh`

**Created**: 2026-10-13

**Status**: Draft

**Input**: "Phase 1 — a seeded synthetic store generator and the store validator. Proven by
AC-14 and every V-rule."

IDs in this file are local to Phase 1 (`P1-…`). The data contract itself is `docs/schema.md`;
this spec does not restate it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A store that refuses bad data names the fault (Priority: P1)

A data author drops a store folder in `data/`. If anything in it breaks a rule in `schema.md` §7,
the store does not load, and the message names the file, the row and the rule, so the author can
fix it without reading code.

**Why this priority**: NFR-07 and AC-14. Every later phase reads store data; a fault caught at
load is a message to an author, a fault caught at request time is a shopper on the wrong floor.

**Independent Test**: for each refusal V-01…V-74, take a valid store, break exactly that rule,
and load it: the load fails and the message carries the rule ID, the file and the row.

**Acceptance Scenarios**:

1. **Given** a store folder breaking one refusal rule, **When** it is loaded, **Then** loading
   stops, nothing is returned, and the message includes the rule ID, the file and — for a row
   fault — the line number.
2. **Given** a store breaking several rules in different files, **When** it is loaded, **Then**
   every fault found in the same validation stage is reported together, not just the first.
3. **Given** a valid store with a suspicious but legitimate pattern (W-01…W-05), **When** it is
   loaded, **Then** it loads and the warning is reported with its ID.

---

### User Story 2 - Unknown stays unknown (Priority: P1)

A dietary flag or allergen declaration left empty in the file is read as *unknown* — never as
"no" — and a malformed boolean such as `TRUE`, `1` or `N/A` is refused rather than guessed.

**Why this priority**: constitution Principle II and NFR-03. Collapsing unknown to false
silently asserts "not gluten free" about products nobody checked.

**Independent Test**: load a store whose products carry `true`, `false` and empty in every
`diet_*` column and `milk|soya`, `none` and empty in `allergens_contains`; each loads as its own
distinct value. `TRUE` in any boolean column is refused with V-04.

**Acceptance Scenarios**:

1. **Given** an empty `diet_halal` cell, **When** the store loads, **Then** that product's halal
   value is unknown, distinct from both true and false.
2. **Given** `allergens_contains` of `none`, **When** the store loads, **Then** it is "checked,
   contains none", distinct from an empty cell.
3. **Given** an empty cell in a two-state column (`ranged`, `is_open`, …), **When** the store
   loads, **Then** it is refused — those columns have no unknown.

---

### User Story 3 - One command produces the demo store, identically every time (Priority: P1)

The builder runs the generator with a seed and gets the six CSV files of the three-floor demo
store, sized as `schema.md` §8 describes. The same seed always gives byte-identical files, so
tests and the demo can rely on exact SKUs and positions.

**Why this priority**: every later phase's tests run against this store.

**Independent Test**: generate twice into two folders; the files are identical. Compare with the
committed `data/SBY-DEMO-001/`; identical. Load it; it passes every refusal.

**Acceptance Scenarios**:

1. **Given** the default seed, **When** the generator runs, **Then** it writes `store.csv` (5
   keys), `products.csv` (180), `stock.csv` (180), `planogram.csv` (about 250),
   `map_nodes.csv` (314) and `map_edges.csv` (352, all bidirectional, 704 arcs).
2. **Given** the committed demo store, **When** the generator is re-run with its seed, **Then**
   the output matches byte for byte — the committed data is never hand-edited.
3. **Given** the demo store, **When** it is loaded, **Then** it passes all refusals and raises
   exactly one warning: W-02 for the deliberate ranged-but-unplaced product (EC-19).

---

### User Story 4 - The demo store contains what later phases must demonstrate (Priority: P2)

The store carries a small set of fixed scenario products whose state does not depend on the seed,
so that each later acceptance test has something real to find.

**Why this priority**: without them AC-01…AC-27 would need hand-made fixtures for every case,
and the live demo would have nothing to show for edge cases.

**Independent Test**: load the demo store and assert each anchor below.

**Acceptance Scenarios** — the anchors:

| For | Anchor in the demo store |
|---|---|
| AC-01, AC-21 | Coca-Cola Classic 500ml, SKU `7123456`: home at `F1-A07-R03` shelf 2, plus a promo end cap at `F1-A07-N` — two placements |
| AC-02 | Milk, bread and eggs all ranged and in stock, on the ground floor |
| AC-03 | Several products answer "milk" — semi-skimmed, whole, skimmed, 4-pint, oat drink |
| AC-05 | In-stock products on every floor |
| AC-16 | Counter products (deli, fish, bakery) and locked-cabinet products (spirits on F1, baby formula on F2) |
| AC-17 | Diet Coke 500ml sold out, with an in-stock alternative of equal recorded dietary attributes in the same category; Gluten Free White Bread sold out, with no gluten-free alternative in its category |
| AC-19, AC-20 | Pepsi Max Cola 500ml not ranged here (`ranged=false`); Diet Coke ranged but sold out |
| AC-25 | Products with unknown dietary attributes (e.g. Coca-Cola's empty `diet_halal`) |
| EC-19 | Sparkling Water Lime 1l ranged and in stock with no placement |
| EC-24 | A sold-out seasonal product |
| EC-33 | Chilled and frozen products in `CHILLER` placements |

### Edge Cases

- A refusal in the parse stage means later stages do not run — their checks would only report
  noise from a file that did not parse.
- A file that is header-only is refused (V-06), except `planogram.csv`.
- A closed node (`is_open=false`) with placements is not an orphan: closure is intentional
  (EC-32), so V-73 checks open nodes only.
- Graph checks run on the open graph, after closed nodes and edges are removed.
- Excel damage: a BOM, a SKU with a lost leading zero, a barcode in scientific notation — each
  refused with its rule.

## Requirements *(mandatory)*

### Functional Requirements

- **P1-R01**: Loading a store folder MUST run every refusal in `schema.md` §7 before returning
  anything, and MUST return nothing if any fails (constitution Principle VI).
- **P1-R02**: Each refusal MUST be reported as `file row N: V-xx — description`; a file-level or
  graph-level fault omits the row.
- **P1-R03**: Validation MUST run in the stages of `lld.md` §13 — parse, within-file,
  referential, graph — and report every fault of the first failing stage together.
- **P1-R04**: A store that passes MUST report each W-rule it triggers, with its ID, and load.
- **P1-R05**: Three-state booleans and the allergen list MUST load as three distinct values;
  two-state booleans MUST refuse an empty cell (`schema.md` §2.2, §2.3).
- **P1-R06**: Text-typed identifier columns (`sku`, `barcode`, node and edge IDs) MUST be read
  as text, never as numbers.
- **P1-R07**: The generator MUST be deterministic for a given seed and MUST write files sorted by
  primary key, UTF-8 without BOM, LF line endings.
- **P1-R08**: The generator MUST produce the demo store at the sizes of `schema.md` §8 and with
  the anchors of User Story 4.
- **P1-R09**: The committed `data/SBY-DEMO-001/` MUST equal the generator's output for its
  recorded seed, checked by a test.
- **P1-R10**: The loader MUST NOT import the graph runtime, a model client or the page framework
  (constitution Principle IV).
- **P1-R11**: Every product, name and identifier MUST be synthetic; no real barcode range is used
  (`schema.md` §9, C-04).

### Key Entities

`schema.md` §4 defines the six files and §6 their relationships. The loaded result is a **Store**:
store info, products, stock positions, placements, map nodes, map edges and the warnings raised.

## Success Criteria *(mandatory)*

- **P1-SC1**: 43 of 43 refusals each have a test that breaks only that rule and sees it named
  in the load failure; 5 of 5 warnings each have a test that triggers it.
- **P1-SC2**: The demo store loads with zero refusals and exactly one warning (W-02).
- **P1-SC3**: Regenerating the demo store from its seed reproduces the committed files byte for
  byte.
- **P1-SC4**: Loading and validating the demo store takes under one second.

## Assumptions

- The schema is amended first with **V-07** (typed cells parse), because without it a cell such
  as `14 units` in `shelf_qty` could not be named by any rule; LLD §13's "forty-seven checks" is
  corrected to 43 refusals and 5 warnings in the same change.
- Unparseable enumerations: `location_type` keeps its own rule (V-42); `node_type` and `kind`
  fall under V-07.
- The loader is `validation.py` with typed records in `models/domain.py` and the error in
  `errors.py`, as `lld.md` §1 places them. The generator is a new top-level `datagen/` package,
  which `lld.md` §1 did not cover because the data was to be hand-authored.
- Graph checks use a breadth-first search in plain Python; `scipy` arrives with the route engine
  in Phase 2, so this phase adds no runtime dependency.
- The portability store (two floors) is generated in Phase 8 by the same generator with a
  different layout; this phase builds only the demo store.
- Brand names such as Coca-Cola appear as a synthetic catalogue's product names, as the
  schema's own worked example does; SKUs, barcodes, prices and stock are invented.
