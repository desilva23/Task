"""resolve_items — every term to ranked catalogue candidates (lld.md §8). Deterministic."""

from services.search import QueryFilter, SearchTerm, resolve

TOP_OPTIONS = 5


def by_barcode(services, s):
    """A barcode is an exact lookup — no ranking, no fuzzy retry, no nearest match (EC-50)."""
    found = services.catalogue.by_barcode(s["terms"][0]["text"])
    return {
        "term_status": ["resolved" if found else "not_catalogued"],
        "candidates": [[found.sku] if found else []],
        "category": [None],
        "suggestions": [[]],
        "resolved": {"0": found.sku} if found else {},
        "unresolved": [],
        "clarify_rounds": 0,
    }


def make_resolve_items(services, model):
    def resolve_items(s):
        if s.get("shape") == "barcode":
            return by_barcode(services, s)
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
            if r.status == "unresolved" and filt and (filt.aisle_category or filt.department):
                # the phrase found nothing, but the model named a real category: offer it
                in_category = sorted(
                    (p for p in services.index.products if filt.admits(p)),
                    key=lambda p: (-p.popularity, p.sku),
                )
                if in_category:
                    status.append("ambiguous")
                    candidates.append([p.sku for p in in_category[:TOP_OPTIONS]])
                    category.append(None)
                    suggestions.append([])
                    continue
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
