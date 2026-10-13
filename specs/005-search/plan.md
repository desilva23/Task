# Implementation Plan: Search (Phase 4)

**Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

Deterministic search per `lld.md` §8 (amended: the "and" guard, the fuzzy retry, categories):
classify, BM25 over the catalogue, one fuzzy retry, a named-rule tuple ranking with `explain`, and
the ambiguity test. A realistic query set measures each layer for the owner's semantic-search
question.

## Technical Context

Python 3.12 · new dependencies `rank-bm25`, `rapidfuzz` (both named by the constitution) ·
pytest · 180 products, so the index builds in milliseconds.

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | Search returns catalogue products only; nothing generated | ✅ |
| II | Dietary filter passes `true` only; unknown allergens never pass an exclusion | ✅ |
| III | Tests first; AC-02/19/26 and EC-01–EC-11 cited | ✅ |
| IV | `services/search.py` imports `rank_bm25`, `rapidfuzz`, services, models, config | ✅ |
| VII | BM25 + one fuzzy retry; no embeddings — measured, not assumed | ✅ |

## Project Structure

```text
config.py                    thresholds from lld.md §14
services/search.py           normalise, classify, SearchIndex, rank, explain, needs_clarification,
                             search_query → QueryResult
services/catalogue.py        Catalogue.search delegates to SearchIndex
services/multistop.py        MultiRoute.stop_at (P4-R08)
tests/unit/test_search.py
tests/unit/test_search_eval.py + tests/fixtures/search_eval.csv
scripts/search_eval.py       prints hit rate per query group (gate evidence)
```

## Complexity Tracking

None.
