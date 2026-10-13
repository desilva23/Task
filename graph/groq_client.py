"""GroqCloud behind the ModelClient adapter (C-06).

Strict structured output is requested directly — ``response_format`` with ``strict: true`` sent
through ``ChatGroq.invoke`` — because LangChain's ``with_structured_output(strict=True)`` is
reported broken for gpt-oss (langchain#34155). Groq's strict mode needs every property in
``required`` and ``additionalProperties: false``, and does not document constraint keywords, so
those are stripped from the schema sent; the node's own validation enforces the full model.

Every failure — timeout, HTTP error, a reply cut off at the token cap, bad JSON, a spent session
budget — becomes ``ModelUnavailableError``, and the node falls back (NFR-04). The key is held,
never shown.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

import config
from errors import ModelUnavailableError

MODELS = {
    "understand": config.MODEL_UNDERSTAND,
    "substitute": config.MODEL_SUBSTITUTE,
    "describe": config.MODEL_DESCRIBE,
}
KEEP = {"type", "properties", "required", "additionalProperties", "items", "enum", "anyOf",
        "$defs", "$ref", "description"}  # fmt: skip


def strict_schema(model: type[BaseModel]) -> dict:
    """The pydantic schema, reshaped for Groq strict mode."""

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        out = {k: walk(v) for k, v in node.items() if k in KEEP or k == "properties"}
        if "properties" in node:
            out["properties"] = {k: walk(v) for k, v in node["properties"].items()}
            out["required"] = list(node["properties"])
            out["additionalProperties"] = False
        return out

    return walk(model.model_json_schema())


def _chat_groq(**params):
    from langchain_groq import ChatGroq  # imported here so the fallbacks never need it

    return ChatGroq(**params)


class GroqClient:
    def __init__(
        self, api_key: str, chat_factory=_chat_groq, budget=config.MODEL_CALLS_PER_SESSION
    ):
        self._key = api_key
        self._factory = chat_factory
        self._chats: dict[str, object] = {}
        self.budget, self.calls = budget, 0

    def __repr__(self) -> str:
        return f"GroqClient(calls={self.calls}/{self.budget})"

    def _chat(self, model_id: str):
        if model_id not in self._chats:
            self._chats[model_id] = self._factory(
                model=model_id,
                api_key=self._key,
                temperature=0,
                max_tokens=config.MODEL_MAX_TOKENS,
                timeout=config.MODEL_TIMEOUT_S,
                max_retries=0,  # the fallback is the retry
                reasoning_effort=config.MODEL_REASONING_EFFORT,
            )
        return self._chats[model_id]

    def complete(self, task: str, schema: type[BaseModel], system: str, user: str) -> dict:
        if self.calls >= self.budget:
            raise ModelUnavailableError("session model budget spent — using the fallbacks")
        self.calls += 1
        fmt = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": strict_schema(schema),
            },
        }
        try:
            reply = self._chat(MODELS[task]).invoke(
                [SystemMessage(content=system), HumanMessage(content=user)], response_format=fmt
            )
            if (reply.response_metadata or {}).get("finish_reason") == "length":
                raise ModelUnavailableError("reply cut off at the token cap")
            return json.loads(reply.content)
        except ModelUnavailableError:
            raise
        except Exception as exc:  # never echo the request, which carries the key in its client
            raise ModelUnavailableError(f"{task} call failed: {type(exc).__name__}") from None
