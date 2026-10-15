"""classify_query — the shape of the request (lld.md §8.2). Pure function.

A scan is checked here too, as digits rather than words (§8.5): a valid code is one term and
skips the model; anything else stops with a message, before any lookup (EC-52)."""

from services.barcode import normalise
from services.search import prepare

BAD_BARCODE = "That isn't a valid barcode — check the digits under the bars and try again."


def make_classify_query(services, model):
    def classify_query(s):
        if s.get("action") == "scan":
            code = normalise(s.get("barcode") or "")
            if code is None:
                return {"shape": "bad_barcode", "terms": [], "message": BAD_BARCODE}
            return {"shape": "barcode", "terms": [{"text": code, "qty": 1}], "message": None}
        p = prepare(s["raw_query"], services.index)
        return {
            "shape": p.shape,
            "terms": [{"text": t.text, "qty": t.qty} for t in p.terms],
            "sentence": p.shape == "nl",
            "message": p.message,
            "split": [{"from": typed, "into": list(items)} for typed, items in p.split],
        }

    return classify_query
