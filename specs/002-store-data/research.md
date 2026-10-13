# Research: Phase 1

## R1. Reading CSV without coercion
- **Decision**: the standard `csv` module, every cell read as a string, typed by an explicit
  per-column parser.
- **Rationale**: `schema.md` §2.2's trap is pandas reading an empty cell as `NaN`. With no
  inference anywhere, unknown cannot collapse to false and a SKU cannot lose a digit.
- **Alternatives**: pandas with `dtype=str, keep_default_na=False` — workable, but a heavy
  dependency whose defaults are exactly the failure mode.

## R2. Stages and fault collection
- **Decision**: four stages per `lld.md` §13 (parse, within-file, referential, graph). All faults
  in a stage are collected; the first stage with any fault stops the load.
- **Rationale**: an author fixes many faults per round trip, while later stages never report
  noise caused by an earlier failure.

## R3. Connectivity without scipy
- **Decision**: forward and reverse BFS over adjacency dicts of the open graph. Strongly
  connected ⇔ one node reaches all and is reached by all.
- **Rationale**: ~700 arcs; BFS is microseconds. scipy is added in Phase 2 when Dijkstra needs it.

## R4. Generator: curated content, seeded details
- **Decision**: product names, categories, aisle positions and scenario anchors are curated in
  `datagen/catalogue.py`; the seed draws SKUs, barcodes, prices, popularity, stock quantities,
  shelf positions, facing counts and the promotional end caps. Anchors override the seed.
- **Rationale**: search tests need believable names, and acceptance tests need anchors that do
  not move when the seed changes. A purely random catalogue would satisfy neither.
- **Barcodes**: EAN-13 with prefix `20` (the restricted in-store range) and a valid check digit —
  never a real manufacturer range.

## R5. Proving each rule
- **Decision**: a session fixture generates the demo store once; each test copies it, applies
  one mutation through small CSV helpers, and asserts the rule ID appears in the failure.
- **Rationale**: every fixture is a known-good store with exactly one fault — the definition of
  AC-14's "malformed store fixture" — with no hand-maintained fixture folders to drift.
