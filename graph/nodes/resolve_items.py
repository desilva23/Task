"""resolve_items — every term to ranked catalogue candidates (lld.md §8). Deterministic."""

from services.search import QueryFilter, SearchTerm, resolve

TOP_OPTIONS = 5


def make_resolve_items(services, model):
    def resolve_items(s):
        parsed = s.get("parsed")
        filt = None
        if parsed:
            filt = QueryFilter(
                department=tuple(parsed["department"]),
                aisle_category=tuple(parsed["aisle_category"]),
                dietary_required=tuple(parsed["dietary_required"]),
                exclude_allergens=tuple(parsed["exclude_allergens"]),
            )
            if filt == QueryFilter():
                filt = None
        status, candidates, category, suggestions, resolved = [], [], [], [], {}
        for i, term in enumerate(s["terms"]):
            r = resolve(
                SearchTerm(term["text"], term["qty"]),
                services.index,
                services.store.stock,
                filt,
                sentence=bool(s.get("sentence")),
            )
            status.append(r.status)
            candidates.append([c.sku for c in r.candidates[:TOP_OPTIONS]])
            category.append(r.category)
            suggestions.append(list(r.suggestions))
            if r.status == "resolved":
                resolved[str(i)] = r.chosen
        return {
            "term_status": status,
            "candidates": candidates,
            "category": category,
            "suggestions": suggestions,
            "resolved": resolved,
            "unresolved": [
                t["text"] for t, st in zip(s["terms"], status, strict=True) if st == "unresolved"
            ],  # fmt: skip
            "clarify_rounds": 0,
        }

    return resolve_items
