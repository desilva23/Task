"""The one adapter between the nodes and any language model (lld.md §6).

``complete`` returns the model's raw output; the node validates it against the schema itself,
so a reply that strays outside the schema is rejected by our code whatever the provider does.
The system prompt carries the instructions; shopper text only ever travels in ``user``, as
data (EC-11). GroqCloud implements this protocol in Phase 6.
"""

import json
import re
from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from errors import ModelUnavailableError


class ModelClient(Protocol):
    def complete(self, task: str, schema: type[BaseModel], system: str, user: str) -> dict: ...


class NoModel:
    """Every call fails — the configuration that proves the fallbacks (AC-11)."""

    def complete(self, task, schema, system, user) -> dict:
        raise ModelUnavailableError(f"no model available for {task}")


Handler = Callable[[type[BaseModel], str, str], dict]


class FakeModel:
    """Scripted responses per task; a task with no handler behaves as unavailable."""

    def __init__(self, **handlers: Handler):
        self.handlers = handlers

    def complete(self, task, schema, system, user) -> dict:
        handler = self.handlers.get(task)
        if handler is None:
            raise ModelUnavailableError(f"no fake for {task}")
        return handler(schema, system, user)


# A well-behaved stand-in: plausible interpretations, an in-set substitute, honest rewording.
_KNOWN = {
    "cat": "cat food",
    "dog": "dog food",
    "headache": "paracetamol",
    "tea": "tea bags",
    "pasta": "pasta",
}


def good_model(services=None) -> FakeModel:
    def understand(schema, system, user):
        words = re.findall(r"[a-z]+", json.loads(user)["query"].lower())
        items = [_KNOWN[w] for w in words if w in _KNOWN]
        return {"items": items[:1]}

    def substitute(schema, system, user):
        candidates = json.loads(user)["candidates"]
        return {"sku": candidates[0]["sku"], "reason": "Closest match in the same aisle."}

    def describe(schema, system, user):
        return {"lines": [f"Next: {line}" for line in json.loads(user)["lines"]]}

    return FakeModel(understand=understand, substitute=substitute, describe=describe)
