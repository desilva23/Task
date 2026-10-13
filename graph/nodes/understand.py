"""understand_query — the model reads a sentence into search phrases and a filter.

Fallback: keep the whole sentence as one keyword term, never auto-resolved (EC-37, EC-38).
"""

import json

from graph import prompts
from graph.nodes.common import degrade
from models.llm import ParsedQuery


def make_understand_query(services, model):
    def understand_query(s):
        try:
            raw = model.complete(
                "understand", ParsedQuery, prompts.UNDERSTAND, json.dumps({"query": s["raw_query"]})
            )
            parsed = ParsedQuery.model_validate(raw)  # a stray field is an error (AC-18)
        except Exception:
            return {"degraded": degrade(s, "understand_query")}
        if not parsed.items:
            return {"parsed": parsed.model_dump()}  # keep the filter; search the sentence
        return {
            "parsed": parsed.model_dump(),
            "terms": [{"text": item, "qty": 1} for item in parsed.items],
            "sentence": False,
        }

    return understand_query
