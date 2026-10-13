"""FR-01 — a realistic query set, measuring each layer of the deterministic search.

This is the evidence for keeping BM25 over embeddings at this catalogue size: exact names,
typos, synonyms, categories and multi-item queries must all land; meaning-style queries may
fail to resolve (that is the model's job, Phase 6) but must never resolve confidently to the
wrong category.
"""

from collections import defaultdict
from functools import cache
from pathlib import Path

from services.search import SearchIndex
from tests.evals.search import evaluate
from validation import load_store

REPO = Path(__file__).resolve().parents[2]


@cache
def report():
    store = load_store(REPO / "data" / "SBY-DEMO-001")
    return evaluate(
        REPO / "tests" / "fixtures" / "search_eval.csv", SearchIndex(store), store.stock
    )


def rate(group):
    rows = [r for r in report() if r.group == group]
    return sum(r.hit for r in rows) / len(rows)


def test_exact_synonym_category_and_multi_queries_all_land():
    misses = defaultdict(list)
    for r in report():
        if r.group in ("exact", "synonym", "category", "multi") and not r.hit:
            misses[r.group].append((r.query, r.got))
    assert not misses


def test_ec_02_at_least_nine_in_ten_typos_land():
    assert rate("typo") >= 0.9, [
        (r.query, r.got) for r in report() if r.group == "typo" and not r.hit
    ]


def test_fr_04_meaning_queries_never_resolve_confidently_to_the_wrong_category():
    wrong = [(r.query, r.got) for r in report() if r.group == "meaning" and r.wrong]
    assert wrong == []
