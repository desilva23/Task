"""Print the search query set's results by group — the evidence behind BM25 over embeddings.

uv run python scripts/search_eval.py
"""

import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.search import SearchIndex  # noqa: E402
from tests.evals.search import evaluate  # noqa: E402
from validation import load_store  # noqa: E402

store = load_store(REPO / "data" / "SBY-DEMO-001")
rows = evaluate(REPO / "tests" / "fixtures" / "search_eval.csv", SearchIndex(store), store.stock)
groups = defaultdict(list)
for r in rows:
    groups[r.group].append(r)

print(f"{'group':<10}{'hit':>8}{'wrong':>8}")
for group, rs in groups.items():
    print(f"{group:<10}{sum(r.hit for r in rs):>4}/{len(rs):<3}{sum(r.wrong for r in rs):>8}")
print()
for r in rows:
    if r.group == "meaning" or not r.hit:
        print(f"  {r.group:<9} {r.query!r:<38} → {r.got}{'  ✗ WRONG' if r.wrong else ''}")
