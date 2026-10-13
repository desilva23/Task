"""The three calls the page makes (lld.md §11) — framework-free, so the page is a thin caller.

``run_query`` searches and returns results (and a route, for one product); ``resume`` answers a
clarification; ``plan_route`` routes the basket. Each is one graph run on the same thread.
"""

import time
from dataclasses import dataclass

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from config import THREAD_TTL_MINUTES
from graph.build import build_graph

FRESH = {
    "parsed": None,
    "sentence": False,
    "message": None,
    "term_status": [],
    "candidates": [],
    "category": [],
    "suggestions": [],
    "resolved": {},
    "unresolved": [],
    "not_ranged": [],
    "notes": [],
    "availability": {},
    "substitutes": {},
    "locations": {},
    "results": [],
    "basket": [],
    "route": None,
    "directions": [],
    "clarify_rounds": 0,
    "degraded": [],
    "errors": [],
    "verified": False,
    "mismatches": [],
}


@dataclass(frozen=True)
class Outcome:
    state: dict
    pending: dict | None  # the clarification to show, if the run paused


class Journey:
    def __init__(self, services, model, checkpointer=None, clock=time.monotonic):
        self.services = services
        self.checkpointer = checkpointer or InMemorySaver()
        self.graph = build_graph(services, model, self.checkpointer)
        self._clock = clock
        self._touched: dict[str, float] = {}

    def _run(self, thread_id: str, payload) -> Outcome:
        cfg = {"configurable": {"thread_id": thread_id}}
        self._touched[thread_id] = self._clock()
        result = self.graph.invoke(payload, cfg)
        pending = result.get("__interrupt__")
        return Outcome(self.graph.get_state(cfg).values, pending[0].value if pending else None)

    def run_query(self, thread_id, query, start_node=None, step_free=False, mode="auto") -> Outcome:
        return self._run(thread_id, {
            **FRESH, "action": "search", "raw_query": query, "mode": mode,
            "start_node": start_node or self.services.engine.graph.entrance,
            "step_free": step_free,
        })  # fmt: skip

    def resume(self, thread_id, choice: dict[str, str]) -> Outcome:
        # wrapped: LangGraph reads a bare dict as answers keyed by interrupt ID
        return self._run(thread_id, Command(resume={"answers": choice}))

    def plan_route(self, thread_id, skus, start_node=None, step_free=False) -> Outcome:
        return self._run(thread_id, {
            **FRESH, "action": "plan", "raw_query": "", "mode": "multi",
            "basket": [{"sku": k} for k in skus],
            "start_node": start_node or self.services.engine.graph.entrance,
            "step_free": step_free,
        })  # fmt: skip

    def sweep(self) -> list[str]:
        """Delete threads idle beyond the TTL — LangGraph never expires them itself (EC-34)."""
        cutoff = self._clock() - THREAD_TTL_MINUTES * 60
        stale = sorted(t for t, at in self._touched.items() if at < cutoff)
        for thread_id in stale:
            self.checkpointer.delete_thread(thread_id)
            del self._touched[thread_id]
        return stale
