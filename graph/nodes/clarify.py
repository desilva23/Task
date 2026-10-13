"""clarify — ask the shopper to choose, then carry on with everything else kept (FR-05).

``interrupt`` re-runs this node on resume, so nothing before it has side effects.
"""

from langgraph.types import interrupt

from graph.templates import product_label


def ambiguous(s: dict) -> list[int]:
    return [
        i
        for i, st in enumerate(s.get("term_status") or [])
        if st == "ambiguous" and str(i) not in (s.get("resolved") or {})
    ]


def make_clarify(services, model):
    def clarify(s):
        open_terms = ambiguous(s)
        questions = [
            {
                "index": str(i),
                "term": s["terms"][i]["text"],
                "options": [
                    {"sku": k, "label": product_label(services, k)} for k in s["candidates"][i]
                ],
            }
            for i in open_terms
        ]
        answer = (interrupt({"questions": questions}) or {}).get("answers") or {}
        resolved, status = dict(s.get("resolved") or {}), list(s["term_status"])
        for i in open_terms:
            choice = answer.get(str(i))
            if choice in s["candidates"][i]:  # only an offered option counts
                resolved[str(i)] = choice
                status[i] = "resolved"
        return {
            "resolved": resolved,
            "term_status": status,
            "clarify_rounds": s.get("clarify_rounds", 0) + 1,
        }

    return clarify
