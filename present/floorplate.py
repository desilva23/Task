"""The floor plates — one SVG per floor the route touches, drawn from the map's coordinates
(FR-20). Pure: returns SVG text and the sequence it draws, so AC-22 is tested without a browser.

Sizes are in metres, the map's own unit; the SVG scales to the container width, so at 390 px a
stop marker is about 20 px across and its number about 12 px tall (AC-15).
"""

from dataclasses import dataclass

MARGIN, MARKER_R, LABEL = 5.0, 2.6, 3.2
ROUTE, STOP, CHANGE = "#0a7d74", "#0a7d74", "#b45309"


@dataclass(frozen=True)
class Segment:
    start: int  # index in the route's node path
    nodes: tuple[str, ...]


@dataclass(frozen=True)
class Plate:
    level: int
    floor_name: str
    svg: str
    segments: tuple[Segment, ...]
    stops: tuple[tuple[int, str], ...]  # (number shown, node)


def _segments(levels: list[int], nodes: list[str]) -> list[tuple[int, Segment]]:
    out, start = [], 0
    for i in range(1, len(nodes) + 1):
        if i == len(nodes) or levels[i] != levels[start]:
            out.append((levels[start], Segment(start, tuple(nodes[start:i]))))
            start = i
    return out


def floor_plates(services, route: dict) -> list[Plate]:
    store, nodes = services.store, route["nodes"]
    levels = [store.nodes[n].level for n in nodes]
    order = list(dict.fromkeys(levels))
    segs = _segments(levels, nodes)
    stops = [(k + 1, st["node_id"]) for k, st in enumerate(route["stops"])]
    changes = [(i - 1, i) for i in range(1, len(nodes)) if levels[i] != levels[i - 1]]
    plates = []
    for level in order:
        mine = tuple(s for lv, s in segs if lv == level)
        my_stops = tuple((n, node) for n, node in stops if store.nodes[node].level == level)
        marks = []
        for a, b in changes:
            way = "up" if levels[b] > levels[a] else "down"
            kind = services.engine.graph.edge(nodes[a], nodes[b], route["step_free"]).kind
            if levels[a] == level:
                marks.append((nodes[a], way, f"{kind} {way} to {levels[b]}"))
            if levels[b] == level:
                marks.append((nodes[b], way, f"from {levels[a]}"))
        svg = _draw(services, level, mine, my_stops, marks, route, nodes[0])
        name = next(n.floor_name for n in store.nodes.values() if n.level == level) or ""
        plates.append(Plate(level, name, svg, mine, my_stops))
    return plates


def _draw(services, level, segments, stops, marks, route, start) -> str:
    here = {i: n for i, n in services.store.nodes.items() if n.level == level}
    xs, ys = [n.x_m for n in here.values()], [n.y_m for n in here.values()]
    x0, y0 = min(xs) - MARGIN, min(ys) - MARGIN
    w, h = max(xs) - min(xs) + 2 * MARGIN, max(ys) - min(ys) + 2 * MARGIN
    out = [
        f'<svg data-floor="{level}" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" width="100%" '
        f'style="display:block;max-width:100%;height:auto" role="img" '
        f'aria-label="Floor {level} map. The directions list above describes the same route.">',
        f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" fill="#f4f5f2"/>',
    ]
    aisles = {}
    for n in here.values():
        if n.node_type == "aisle_end":
            aisles.setdefault(n.aisle, []).append(n)
    for ends in aisles.values():
        a, b = sorted(ends, key=lambda n: n.y_m)[0], sorted(ends, key=lambda n: n.y_m)[-1]
        out.append(f'<line x1="{a.x_m}" y1="{a.y_m}" x2="{b.x_m}" y2="{b.y_m}" '
                   'stroke="#d5d8d0" stroke-width="2.4" stroke-linecap="round"/>')  # fmt: skip
    for n in here.values():
        if n.node_type in ("till", "counter", "cabinet", "core", "entrance", "bin"):
            out.append(f'<circle cx="{n.x_m}" cy="{n.y_m}" r="1.1" fill="#8a8f85"/>')
    nodes = services.store.nodes
    for seg in segments:
        pts = " ".join(f"{nodes[i].x_m},{nodes[i].y_m}" for i in seg.nodes)
        out.append(f'<polyline data-route="{" ".join(seg.nodes)}" points="{pts}" fill="none" '
                   f'stroke="{ROUTE}" stroke-width="1.2" stroke-linejoin="round" '
                   'stroke-linecap="round"/>')  # fmt: skip
    if nodes[start].level == level:
        s = nodes[start]
        out.append(f'<g data-start="{start}"><rect x="{s.x_m - 2.4}" y="{s.y_m - 2.4}" '
                   f'width="4.8" height="4.8" rx="1" fill="#1f2937"/></g>')  # fmt: skip
    by_node: dict[str, set[str]] = {}
    for node_id, way, _ in marks:
        by_node.setdefault(node_id, set()).add(way)
    for node_id, ways in by_node.items():
        n = nodes[node_id]
        glyph = "⇅" if len(ways) > 1 else ("↑" if "up" in ways else "↓")
        # one marker per core, however often the route passes it; the directions list says
        # which connector and which floor, so the map carries no overlapping text
        out.append(
            f'<g data-transition="{" ".join(sorted(ways))}" data-node="{node_id}">'
            f'<rect x="{n.x_m - 2.4}" y="{n.y_m - 2.4}" width="4.8" height="4.8" rx="0.8" '
            f'fill="{CHANGE}"/><text x="{n.x_m}" y="{n.y_m + LABEL * 0.36}" font-size="{LABEL}" '
            f'text-anchor="middle" fill="#fff" font-family="sans-serif">{glyph}</text></g>'
        )
    if route.get("till") and nodes[route["till"]].level == level:
        t = nodes[route["till"]]
        out.append(f'<g data-till="{route["till"]}"><circle cx="{t.x_m}" cy="{t.y_m}" r="2" '
                   'fill="#1f2937"/></g>')  # fmt: skip
    for number, node_id in stops:
        n = nodes[node_id]
        out.append(
            f'<g data-stop="{number}" data-node="{node_id}">'
            f'<circle cx="{n.x_m}" cy="{n.y_m}" r="{MARKER_R}" fill="{STOP}" stroke="#fff" '
            f'stroke-width="0.6"/><text x="{n.x_m}" y="{n.y_m + LABEL * 0.36}" '
            f'font-size="{LABEL}" font-weight="700" text-anchor="middle" fill="#fff" '
            f'font-family="sans-serif">{number}</text></g>'
        )
    out.append("</svg>")
    return "".join(out)
