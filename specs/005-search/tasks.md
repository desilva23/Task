---
description: "Task list for Phase 4 — search"
---

# Tasks: Search (Phase 4)

- [X] T001 Amend `docs/lld.md` §8 (and-guard, fuzzy retry, categories, named rules) — spec first
- [X] T002 Add `rank-bm25`, `rapidfuzz`; fill `config.py` from `lld.md` §14
- [X] T003 Write failing `tests/unit/test_search.py`: classify (EC-01, EC-06, EC-10, quantities, and-guard), AC-02, AC-19, AC-26 (ranking and route halves), ambiguity (FR-05, EC-05), fuzzy (EC-02), synonyms, categories (EC-09), no match (EC-03), dedupe (EC-07), partial (EC-08), dietary filter (NFR-03), injection as data (EC-11)
- [X] T004 Write the query set `tests/fixtures/search_eval.csv` and failing `tests/unit/test_search_eval.py` (P4-SC2)
- [X] T005 Implement `services/search.py`, `Catalogue.search`, `MultiRoute.stop_at` until T003–T004 pass
- [X] T006 `scripts/search_eval.py`; timings (P4-SC3); regenerate the matrix; `scripts/check.sh` green; gate record

## Gate record (2026-10-13)

- `scripts/check.sh` green. AC-02, AC-19, AC-26 proven; also EC-01, EC-02, EC-03, EC-05, EC-06,
  EC-07, EC-08, EC-09, EC-10, EC-11, FR-01, FR-02, FR-05, FR-06, NFR-03, NFR-09.
- Query set (`uv run python scripts/search_eval.py`), deterministic search only:

  | Group | Hit | Confidently wrong |
  |---|---|---|
  | exact | 12/12 | 0 |
  | typo | 14/14 | 0 |
  | synonym | 11/11 | 0 |
  | category | 5/5 | 0 |
  | multi-item | 6/6 | 0 |
  | meaning-style | 3/6 | 0 |

  Meaning-style sentences are the model's job (Phase 6); without it they are offered as a
  choice, never asserted. This is the evidence for BM25 over embeddings at 180 products.
- Timing: index 1.6 ms; one term 0.1–1.6 ms; a 30-term batch 2.3 ms (P4-SC3).
- Decisions for the owner: `FUZZY_THRESHOLD` 80 → 75, measured — every typo lands with no new
  false correction; the "and" guard runs before the split (the LLD's retry could not catch
  "salt and vinegar crisps"); newlines survive classification (an LLD pseudocode bug); a keyword
  fallback for a sentence is never marked resolved.
