"""describe_route — the model rewords the template's fact lines; fallback is the template."""

import json

from graph import prompts
from graph.nodes.common import degrade
from graph.templates import directions
from models.llm import RouteDescription


def make_describe_route(services, model):
    def describe_route(s):
        facts = directions(services, s.get("route"))
        if not s.get("route") or s["route"]["kind"] == "none":
            return {"directions": facts}
        try:
            out = RouteDescription.model_validate(
                model.complete(
                    "describe", RouteDescription, prompts.DESCRIBE, json.dumps({"lines": facts})
                )
            )
            if len(out.lines) != len(facts):
                raise ValueError("one line per fact line")
            return {"directions": out.lines}
        except Exception:
            return {"directions": facts, "degraded": degrade(s, "describe_route")}

    return describe_route
