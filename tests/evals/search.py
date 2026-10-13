"""The search query set: each row's query, what it should find, and what it found."""

import csv
from dataclasses import dataclass
from pathlib import Path

from services.search import SearchIndex, search_query


@dataclass(frozen=True)
class EvalRow:
    group: str
    query: str
    expect: str
    got: str
    hit: bool
    wrong: bool = False  # confident and wrong — the failure that matters


def evaluate(path: Path, index: SearchIndex, stock) -> list[EvalRow]:
    rows = []
    for row in csv.DictReader(path.open()):
        group, query, expect = row["group"], row["query"], row["expect"]
        result = search_query(query, index, stock)
        first = result.terms[0] if result.terms else None
        top = None
        if first and first.chosen:
            top = services_product(index, first.chosen)
        elif first and first.candidates:
            top = first.candidates[0].product
        if group == "category":
            got = f"{first.status}:{first.category}" if first else result.shape
            hit = bool(first) and first.status == "category" and first.category == expect
            rows.append(EvalRow(group, query, expect, got, hit))
        elif group == "multi":
            got = str(len(result.terms))
            hit = len(result.terms) == int(expect) and all(t.candidates for t in result.terms)
            rows.append(EvalRow(group, query, expect, got, hit))
        elif group == "meaning":
            allowed = expect.split("|")
            got = (
                f"{first.status}:{top.aisle_category}" if top else (first.status if first else "-")
            )
            hit = top is not None and top.aisle_category in allowed
            wrong = bool(first) and first.status == "resolved" and not hit
            rows.append(EvalRow(group, query, expect, got, hit, wrong))
        else:
            got = top.name if top else (first.status if first else result.shape)
            rows.append(EvalRow(group, query, expect, got, got == expect))
    return rows


def services_product(index: SearchIndex, sku: str):
    return next(p for p in index.products if p.sku == sku)
