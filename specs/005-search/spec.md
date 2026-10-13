# Feature Specification: Search (Phase 4)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-13 ·
**Status**: Draft

**Input**: "Phase 4 — search: classify, BM25, fuzzy, ranking, ambiguity. Proven by AC-02, AC-19,
AC-26." Owner's question at the gate: would semantic search beat BM25, and does fuzzy matching
cope? Answered with a measured query set (User Story 4).

IDs here are local (`P4-…`). The design is `lld.md` §8; this spec does not restate it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One box, one or many products (Priority: P1)

A shopper types a product, or several separated by commas, semicolons, new lines or "and", and
gets one result per product. A product whose name contains "and" stays one product.

**Acceptance Scenarios**:
1. **Given** "milk, bread, eggs", **Then** three separate results come back, one per term (AC-02,
   FR-02).
2. **Given** "salt and vinegar crisps", **Then** one result, the crisps — not salt plus crisps.
3. **Given** "2 x milk", **Then** one term, "milk", quantity 2.
4. **Given** an empty or one-character query, or digits only, **Then** no search runs and the
   reason is stated (EC-01, EC-10).
5. **Given** 200 pasted terms, **Then** the first 30 are searched and the rest returned unprocessed
   with a message (EC-06).
6. **Given** "milk, milk, bread", **Then** duplicates are merged after resolution (EC-07); one term
   that matches nothing does not fail the others (EC-08).

### User Story 2 - The right product first, for a reason anyone can read (Priority: P1)

Results are ranked by a fixed precedence: carried here, in stock, size asked for, text match,
popularity, own brand. Each result's position is explained by the first rule that separates it
from the one above.

**Acceptance Scenarios**:
1. **Given** a term matching a ranged and an unranged product, **Then** the ranged one ranks first
   even if the unranged one matches the text better (AC-19, FR-06).
2. **Given** any ranked list, **Then** every adjacent pair is explained by exactly one named rule,
   with no model involved (AC-26, NFR-09).
3. **Given** any multi-stop route, **Then** its stop order can be read straight off its node path
   (AC-26).
4. **Given** "milk", where several products match about equally, **Then** the result is marked
   ambiguous so the shopper can be asked (FR-05, EC-05); "Coca-Cola Classic" is not ambiguous.

### User Story 3 - Typos, other words, and categories (Priority: P1)

**Acceptance Scenarios**:
1. **Given** a misspelling such as "paracetomol", **Then** a weak text match triggers one fuzzy
   retry, and the product is found (EC-02).
2. **Given** a word in a product's synonyms ("spuds", "loo roll"), **Then** that product is found.
3. **Given** a department or category name that no product is named after ("dairy", "frozen"),
   **Then** the result is the category, not an arbitrary product (EC-09).
4. **Given** nothing matches, **Then** "not recognised" with up to three nearest suggestions —
   never an empty answer (EC-03).
5. **Given** a dietary filter (from the model, Phase 6), **Then** only products whose attribute is
   recorded `true` pass; unknown never satisfies it, and an unknown allergen declaration never
   passes an allergen exclusion (Principle II, NFR-03).

### User Story 4 - Measured, not argued (Priority: P2)

A realistic query set — exact names, typos, synonyms, categories, multi-item and meaning-style
queries — is run through the deterministic search and the hit rate per group is reported at the
gate.

**Acceptance Scenarios**:
1. **Given** the query set, **Then** exact, synonym, category and multi-item queries all hit, and at
   least 90% of typo queries hit.
2. **Given** meaning-style queries ("something for a headache"), **Then** the deterministic search
   never resolves them to a product outside the expected category — it may fail to resolve, which
   is the model's job in Phase 6, but it must not guess wrong.

### Edge Cases

- A typo and a real word close together (`cola` / `coal`): fuzzy correction only runs when BM25 is
  weak, and only corrects to words in the catalogue's own vocabulary.
- Prompt-injection text in a query is searched as plain data and simply fails to match (EC-11).
- Non-English or accented input is normalised to ASCII before matching.

## Requirements *(mandatory)*

- **P4-R01**: `classify` per `lld.md` §8.2; before splitting on "and", the whole query is kept as
  one term if one product's name contains every one of its words.
- **P4-R02**: BM25 index per §8.1 (k1 1.2, b 0.5) over name, brand, size, category and synonyms.
- **P4-R03**: If the best BM25 score is below `FUZZY_TRIGGER_SCORE`, retry once: correct each query
  word to the nearest catalogue word (ratio ≥ `FUZZY_THRESHOLD`); if that still finds nothing,
  match whole product names with rapidfuzz `WRatio` ≥ `FUZZY_THRESHOLD`.
- **P4-R04**: `rank` is the §8.3 tuple sort; `explain` names, for each result after the first,
  the first rule separating it from its neighbour.
- **P4-R05**: `needs_clarification` per §8.4 (relative margin 0.15, at least 3 hits).
- **P4-R06**: Category detection: a term equal to a department or category name that appears in no
  product name returns the category.
- **P4-R07**: Every threshold lives in `config.py` (`lld.md` §14).
- **P4-R09**: A sentence-shaped query searched by keywords (the model's fallback, EC-37) is never
  marked resolved: its best matches are offered as a choice, because keyword-matching a sentence
  is a guess.
- **P4-R08**: `MultiRoute` records where in its node path each stop is picked, so stop order is
  reproducible from the path.

## Success Criteria *(mandatory)*

- **P4-SC1**: AC-02, AC-19, AC-26 pass.
- **P4-SC2**: Query-set hit rates: exact, synonym, category, multi-item 100%; typo ≥ 90%;
  meaning-style — zero wrong resolutions.
- **P4-SC3**: A single-term search takes under 20 ms; a 30-term batch under 300 ms.

## Assumptions

- Semantic (embedding) search is not added: meaning-style queries go to the model in Phase 6, and
  the measured query set is the evidence for that choice (`CLAUDE.md` settled decision; owner's
  question answered at the gate).
- The clarify interrupt itself is the graph's (Phase 5); search only marks a result ambiguous.
