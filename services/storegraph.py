"""StoreGraph — the open, walkable graph the matrices are built from (lld.md §4, schema.md §4.6).

Only open nodes and open edges between them exist here (EC-30, EC-32). Each edge row becomes
one or two directed arcs with effective weight ``weight_m + penalty_m``. Parallel arcs collapse
to the cheapest — **after** filtering to step-free edges for the step-free graph, or the
stairs' lower weight would hide the lift.
"""

from scipy.sparse import csr_matrix

from models.domain import MapEdge, MapNode, Store


class StoreGraph:
    def __init__(self, store: Store, closed_edges: frozenset[str] = frozenset()):
        self.store = store
        self.closed_edges = frozenset(closed_edges)
        self.nodes: dict[str, MapNode] = {i: n for i, n in store.nodes.items() if n.is_open}
        self.rev: list[str] = sorted(self.nodes)
        self.index: dict[str, int] = {node_id: i for i, node_id in enumerate(self.rev)}
        self.entrance = next(i for i, n in self.nodes.items() if n.node_type == "entrance")
        self._arcs: dict[tuple[str, str], list[MapEdge]] = {}
        for e in store.edges:
            if not e.is_open or e.edge_id in self.closed_edges:
                continue
            if e.from_node not in self.nodes or e.to_node not in self.nodes:
                continue
            pairs = [(e.from_node, e.to_node)]
            if e.bidirectional:
                pairs.append((e.to_node, e.from_node))
            for pair in pairs:
                self._arcs.setdefault(pair, []).append(e)

    def edge(self, u: str, v: str, step_free: bool = False) -> MapEdge | None:
        """The edge a walker takes from u to v: the cheapest one allowed in this mode."""
        allowed = [e for e in self._arcs.get((u, v), []) if e.step_free or not step_free]
        return min(allowed, key=lambda e: (e.weight_m + e.penalty_m, e.edge_id), default=None)

    def csr(self, step_free: bool = False) -> csr_matrix:
        rows, cols, weights = [], [], []
        for u, v in self._arcs:
            e = self.edge(u, v, step_free)
            if e is not None:
                rows.append(self.index[u])
                cols.append(self.index[v])
                weights.append(e.weight_m + e.penalty_m)
        n = len(self.rev)
        return csr_matrix((weights, (rows, cols)), shape=(n, n))

    def without(self, edge_ids) -> "StoreGraph":
        """The same store with more edges closed — a lift out of service (EC-30)."""
        return StoreGraph(self.store, self.closed_edges | set(edge_ids))
