"""understand_query — the model reads a sentence into search phrases and a filter.

Fallback: keep the whole sentence as one keyword term, never auto-resolved (EC-37, EC-38).
"""

import json

from graph import prompts
from graph.nodes.common import degrade


def file_names(parsed: dict, store) -> dict:
    """Put each store name the model chose into the field it belongs to."""
    categories = {p.aisle_category for p in store.products.values()}
    departments = {p.department for p in store.products.values()}
    chosen = list(dict.fromkeys(parsed["department"] + parsed["aisle_category"]))
    return {
        **parsed,
        "aisle_category": [n for n in chosen if n in categories],
        "department": [n for n in chosen if n in departments and n not in categories],
    }


def make_understand_query(services, model):
    def understand_query(s):
        try:
            schema = services.query_model
            raw = model.complete(
                "understand", schema, prompts.UNDERSTAND, json.dumps({"query": s["raw_query"]})
            )
            parsed = schema.model_validate(raw)  # a stray field or invented name is an error
        except Exception:
            return {"degraded": degrade(s, "understand_query")}
        filed = file_names(parsed.model_dump(), services.store)
        if not parsed.items:
            return {"parsed": filed}  # keep the filter; search the sentence
        return {
            "parsed": filed,
            "terms": [{"text": item, "qty": 1} for item in parsed.items],
            "sentence": False,
        }

    return understand_query
