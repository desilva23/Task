"""RouteEngine — all-pairs shortest paths, precomputed once (lld.md §4, §10 single).

The layout is static, so Dijkstra runs from every node at startup, for the full graph and for
the step-free graph. Every request is then a matrix read: ``distance`` is O(1) and ``path``
walks the predecessor matrix, O(path length).
"""

import math

import numpy as np
from scipy.sparse.csgraph import shortest_path

from errors import InvalidNodeError, UnreachableNodeError
from models.domain import MapEdge, NoRoute, Placement, Route
from services.storegraph import StoreGraph

NO_PATH = -9999  # scipy's predecessor sentinel


class RouteEngine:
    def __init__(self, graph: StoreGraph):
        self.graph = graph
        self.D_full, self.P_full = self._solve(step_free=False)
        self.D_step, self.P_step = self._solve(step_free=True)

    def _solve(self, step_free: bool) -> tuple[np.ndarray, np.ndarray]:
        return shortest_path(
            self.graph.csr(step_free), method="D", directed=True, return_predecessors=True
        )

    def _ix(self, node_id: str) -> int:
        try:
            return self.graph.index[node_id]
        except KeyError:
            raise InvalidNodeError(node_id) from None

    def distance(self, u: str, v: str, step_free: bool = False) -> float:
        """Shortest walking distance in metres; ``inf`` if there is no path in this mode."""
        D = self.D_step if step_free else self.D_full
        return float(D[self._ix(u), self._ix(v)])

    def path(self, u: str, v: str, step_free: bool = False) -> list[str]:
        P = self.P_step if step_free else self.P_full
        i, j = self._ix(u), self._ix(v)
        if i == j:
            return [u]  # EC-25, zero-length
        if P[i, j] == NO_PATH:
            raise UnreachableNodeError(u, v)  # EC-29
        out, k = [v], j
        while k != i:
            k = int(P[i, k])
            out.append(self.graph.rev[k])
        return list(reversed(out))

    def hops(self, nodes: list[str], step_free: bool = False) -> list[MapEdge]:
        """The edge used for each hop — what lets directions say lift or stairs."""
        return [self.graph.edge(a, b, step_free) for a, b in zip(nodes, nodes[1:], strict=False)]

    def route_single(
        self, start: str, placements: list[Placement], step_free: bool = False
    ) -> Route | NoRoute:
        """Route to the nearest routable placement (FR-11, FR-13, EC-20)."""
        self._ix(start)
        if not placements:
            return NoRoute("no_location", "This product has no recorded location in the store.")
        open_ = [p for p in placements if p.node_id in self.graph.index]
        if not open_:
            return NoRoute("no_open_location", "Where this product is kept is closed right now.")
        target = min(open_, key=lambda p: (self.distance(start, p.node_id, step_free), p.node_id))
        distance = self.distance(start, target.node_id, step_free)
        if math.isinf(distance):
            if step_free and any(math.isfinite(self.distance(start, p.node_id)) for p in open_):
                return NoRoute(
                    "no_step_free_route",
                    "There is no step-free route to this product right now — every way "
                    "there uses stairs.",
                )
            raise UnreachableNodeError(start, target.node_id)
        nodes = self.path(start, target.node_id, step_free)
        floors = tuple(dict.fromkeys(self.graph.nodes[n].level for n in nodes))
        return Route(tuple(nodes), distance, floors, target, step_free)

    def closed(self, edge_ids) -> "RouteEngine":
        """A new engine with these edges out of service, matrices rebuilt (EC-30)."""
        return RouteEngine(self.graph.without(edge_ids))
