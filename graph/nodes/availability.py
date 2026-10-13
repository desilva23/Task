"""check_availability — one batched stock read; unknown is marked, never guessed (EC-18)."""

from graph.nodes.clarify import ambiguous


def make_check_availability(services, model):
    def check_availability(s):
        resolved, status = dict(s.get("resolved") or {}), list(s.get("term_status") or [])
        notes = list(s.get("notes") or [])
        for i in ambiguous(s):  # clarification capped (EC-35): use the top-ranked option
            resolved[str(i)] = s["candidates"][i][0]
            status[i] = "resolved"
            notes.append(f"For “{s['terms'][i]['text']}” we used the top match.")
        skus = list(dict.fromkeys(resolved.values()))
        return {
            "resolved": resolved,
            "term_status": status,
            "notes": notes,
            "availability": {k: services.stock.availability(k).value for k in skus},
            "not_ranged": [k for k in skus if services.stock.availability(k).value == "not_ranged"],
        }

    return check_availability
