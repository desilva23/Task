"""classify_query — the shape of the request (lld.md §8.2). Pure function."""

from services.search import prepare


def make_classify_query(services, model):
    def classify_query(s):
        p = prepare(s["raw_query"], services.index)
        return {
            "shape": p.shape,
            "terms": [{"text": t.text, "qty": t.qty} for t in p.terms],
            "sentence": p.shape == "nl",
            "message": p.message,
        }

    return classify_query
