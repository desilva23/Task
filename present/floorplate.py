"""The floor plates — one SVG per floor the route touches, drawn from the map's coordinates
(FR-20). Pure: returns SVG text and the sequence it draws, so AC-22 is tested without a browser.

The plate is meant to be read without explanation. The store is wide and shallow, so the plan
is turned a quarter for a phone held upright — the front of the store on the right, the rear wall
on the left — and every feature carries words: each aisle its number and what it sells, the
counters and locked cabinets their names, both stairs-and-lift cores, the checkouts and the
entrance, where the route starts, each product picked with its rack and shelf, and where to
change floor and to which floor. Sizes are in metres, the map's own unit; the SVG scales to the
container width, so at 390 px a stop marker is about 20 px across and its text at least 11 px
tall (AC-15).
"""

from dataclasses import dataclass
from html import escape

# sizes in metres of the drawing
PAD_L, PAD_R = 4.6, 11.0  # room for the words around the plan
FONT, SMALL = 2.0, 1.65
MARKER_R, AISLE_W = 1.6, 1.6
ROUTE, STOP, CHANGE, INK, MUTED = "#0a7d74", "#0a7d74", "#b45309", "#1f2937", "#5d6662"
FLOOR_BG, SHELF, SERVICE = "#f4f5f2", "#d5d8d0", "#e8e2d4"
HALO = 'paint-order="stroke" stroke="#f4f5f2" stroke-width="0.55" stroke-linejoin="round"'
SANS = 'font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif"'


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
    stops = [(k + 1, st["node_id"], st["sku"]) for k, st in enumerate(route["stops"])]
    changes = [(i - 1, i) for i in range(1, len(nodes)) if levels[i] != levels[i - 1]]
    plates = []
    for level in order:
        mine = tuple(s for lv, s in segs if lv == level)
        my_stops = [(n, node, sku) for n, node, sku in stops if store.nodes[node].level == level]
        marks = []
        for a, b in changes:
            way = "up" if levels[b] > levels[a] else "down"
            kind = services.engine.graph.edge(nodes[a], nodes[b], route["step_free"]).kind
            if levels[a] == level:
                marks.append((nodes[a], way, f"{kind.capitalize()} {way} to floor {levels[b]}"))
            if levels[b] == level:
                marks.append((nodes[b], way, f"Arrive from floor {levels[a]} by {kind}"))
        name = next(n.floor_name for n in store.nodes.values() if n.level == level) or ""
        svg = _draw(services, level, name, mine, my_stops, marks, route, nodes[0])
        plates.append(Plate(level, name, svg, mine, tuple((n, node) for n, node, _ in my_stops)))
    return plates


# ── drawing ──────────────────────────────────────────────────────────────────────────────────


def _text(x, y, words, size=None, anchor="start", weight=400, fill=None, extra=""):
    size, fill = size or FONT, fill or INK
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" {SANS} {HALO} {extra}>{escape(words)}</text>')  # fmt: skip


def _width(words: str, size: float) -> float:
    return len(words) * size * 0.56  # a fair average for this face; used only to avoid overlaps


def _shelf(services, sku: str, node_id: str) -> str:
    for p in services.planogram.for_sku(sku):
        if p.node_id == node_id and p.shelf_no:
            return f"shelf {p.shelf_no}"
    return ""


class _Labels:
    """Places one-line labels so that none overlaps another: a label that would collide moves
    down a line. Overlaps with the route line are allowed — every label has a halo."""

    def __init__(self):
        self.taken: list[tuple[float, float, float, float]] = []  # (top, bottom, left, right)

    def place(self, x, y, words, size, anchor="start", lo=None, hi=None):
        span = _width(words, size)
        left = x - span if anchor == "end" else x
        if lo is not None:
            left = max(left, lo)
        if hi is not None:
            left = min(left, hi - span)
        while any(top < y + 0.4 and y - size < bottom and left < rx and left + span > lx
                  for top, bottom, lx, rx in self.taken):  # fmt: skip
            y += size + 0.35
        self.taken.append((y - size, y + 0.4, left, left + span))
        return left, y


def _draw(services, level, floor_name, segments, stops, marks, route, start) -> str:
    store = services.store
    nodes = store.nodes
    here = {i: n for i, n in nodes.items() if n.level == level}
    x_max = max(n.x_m for n in here.values())
    y_min, y_max = min(n.y_m for n in here.values()), max(n.y_m for n in here.values())
    mid_y = (y_min + y_max) / 2

    def at(node_id):  # a quarter turn: the store's depth across, its width down
        n = nodes[node_id]
        return n.y_m, x_max - n.x_m

    # floor changes, as short lines beside their core: the rear core's go above the plan, the
    # front core's below it, where nothing else is drawn
    events: dict[str, list[str]] = {}
    for node_id, way, words in marks:
        events.setdefault(node_id, []).append(("↑ " if way == "up" else "↓ ") + words)
    rear_lines = sum(len(v) for k, v in events.items() if at(k)[1] < x_max / 2)
    front_lines = sum(len(v) for k, v in events.items() if at(k)[1] >= x_max / 2)
    line = FONT + 0.5
    pad_t = 8.5 + rear_lines * line
    pad_b = 10.0 + front_lines * line
    left, top = y_min - PAD_L, -pad_t
    w, h = (y_max - y_min) + PAD_L + PAD_R, x_max + pad_t + pad_b
    right = left + w
    labels = _Labels()
    out = [
        f'<svg data-floor="{level}" viewBox="{left:.1f} {top:.1f} {w:.1f} {h:.1f}" width="100%" '
        f'style="display:block;max-width:100%;height:auto" role="img" '
        f'aria-label="Floor {level} map. The directions list above describes the same route.">',
        f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" fill="{FLOOR_BG}"/>',
        _text(left + 1.2, top + 3.0, f"Floor {level} · {floor_name}", size=2.4, weight=700),
        _text(left + 1.2, top + 5.9, "◀ rear of store", size=SMALL, fill=MUTED),
        _text(right - 1.2, top + 5.9, "front of store ▶", size=SMALL, anchor="end", fill=MUTED),
    ]

    # aisles: a shelf bar each, its number and what it sells written along it
    aisles: dict[int, list] = {}
    for node_id, n in here.items():
        if n.node_type in ("aisle_end", "rack"):
            aisles.setdefault(n.aisle, []).append(node_id)
    for aisle, ids in sorted(aisles.items()):
        pts = sorted(at(i) for i in ids)
        (x1, y), (x2, _) = pts[0], pts[-1]
        zone = next((here[i].zone for i in ids if here[i].node_type == "rack"), "") or ""
        out.append(f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" stroke="{SHELF}" '
                   f'stroke-width="{AISLE_W}" stroke-linecap="round"/>')  # fmt: skip
        words = f"Aisle {aisle} · {zone}"
        lx, ly = labels.place(x1 + 1.6, y - AISLE_W / 2 - 0.35, words, SMALL)
        out.append(_text(lx, ly, words, size=SMALL, fill="#3d4440", weight=600,
                         extra=f'data-aisle="{aisle}"'))  # fmt: skip

    # the places with names: counters, locked cabinets, checkouts, the entrance, stairs and lifts
    tills = sorted((at(i) for i, n in here.items() if n.node_type == "till"), key=lambda p: p[1])
    for x, y in tills:
        out.append(f'<rect x="{x - 1:.2f}" y="{y - 1.2:.2f}" width="2" height="2.4" rx="0.4" '
                   f'fill="{SERVICE}" stroke="{MUTED}" stroke-width="0.2"/>')  # fmt: skip
    if tills:
        lx, ly = labels.place(
            tills[0][0] - 1.0, tills[0][1] - 2.0, "Checkouts", FONT, hi=right - 0.8
        )
        out.append(_text(lx, ly, "Checkouts", weight=700))
    for node_id, n in here.items():
        x, y = at(node_id)
        if n.node_type in ("counter", "cabinet"):
            words = n.zone.removesuffix(" Counter") + (
                " (locked)" if n.node_type == "cabinet" else ""
            )
            out.append(f'<rect x="{x - 1.2:.2f}" y="{y - 1.2:.2f}" width="2.4" height="2.4" '
                       f'rx="0.4" fill="{SERVICE}" stroke="{MUTED}" stroke-width="0.2"/>')  # fmt: skip
            # along the rear wall, upright, so the name never crosses an aisle
            out.append(_text(x - 1.7, y, words, size=SMALL, anchor="middle", weight=700,
                             extra=f'transform="rotate(-90 {x - 1.7:.2f} {y:.2f})"'))  # fmt: skip
        elif n.node_type == "entrance":
            out.append(f'<path d="M{x + 2.2:.2f} {y - 1.4:.2f} l-2 1.4 l2 1.4" fill="none" '
                       f'stroke="{INK}" stroke-width="0.5"/>')  # fmt: skip
            lx, ly = labels.place(x + 2.6, y + 0.7, "Entrance", FONT, hi=right - 0.6)
            out.append(_text(lx, ly, "Entrance", weight=700))
        elif n.node_type == "core":
            out.append(f'<rect x="{x - 1.4:.2f}" y="{y - 1.4:.2f}" width="2.8" height="2.8" '
                       f'rx="0.5" fill="#fff" stroke="{CHANGE}" stroke-width="0.35"/>'
                       f'<text x="{x:.2f}" y="{y + 0.7:.2f}" font-size="{FONT}" text-anchor="middle" '
                       f'fill="{CHANGE}" {SANS}>⇅</text>')  # fmt: skip
            front = x > mid_y
            lx, ly = labels.place(x + (-2.4 if front else 2.4), y + 0.7, "Stairs & lift", SMALL,
                                  anchor="end" if front else "start")  # fmt: skip
            out.append(_text(lx, ly, "Stairs & lift", size=SMALL, weight=700, fill=CHANGE))

    # the route
    for seg in segments:
        pts = " ".join(f"{at(i)[0]:.2f},{at(i)[1]:.2f}" for i in seg.nodes)
        out.append(f'<polyline data-route="{" ".join(seg.nodes)}" points="{pts}" fill="none" '
                   f'stroke="{ROUTE}" stroke-width="0.9" stroke-linejoin="round" '
                   'stroke-linecap="round" opacity="0.9"/>')  # fmt: skip
    if nodes[start].level == level:
        x, y = at(start)
        lx, ly = labels.place(x + 2.6, y + 0.7, "Start here", FONT, hi=right - 0.6)
        out.append(
            f'<g data-start="{start}"><circle cx="{x:.2f}" cy="{y:.2f}" r="1.3" '
            f'fill="{INK}" stroke="#fff" stroke-width="0.4"/>'
            + _text(lx, ly, "Start here", weight=700)
            + "</g>"
        )
    if route.get("till") and nodes[route["till"]].level == level:
        x, y = at(route["till"])
        lx, ly = labels.place(x + 1.8, y + 0.7, "Pay here", FONT, hi=right - 0.6)
        out.append(
            f'<g data-till="{route["till"]}"><circle cx="{x:.2f}" cy="{y:.2f}" r="1.4" '
            f'fill="{INK}" stroke="#fff" stroke-width="0.4"/>'
            + _text(lx, ly, "Pay here", weight=700)
            + "</g>"
        )

    # changing floor: where, which way, by what, to which floor
    for node_id, lines in events.items():
        x, y = at(node_id)
        ways = {m[1] for m in marks if m[0] == node_id}
        glyph = "⇅" if len(ways) > 1 else ("↑" if "up" in ways else "↓")
        rear = y < x_max / 2
        first = (top + 8.2 + FONT) if rear else (y + 2.6 + FONT)
        anchor = "start" if x < mid_y else "end"
        tx = max(left + 1.2, x - 1.4) if anchor == "start" else min(right - 1.2, x + 1.4)
        texts = "".join(_text(tx, first + k * line, words, anchor=anchor, weight=700, fill=CHANGE)
                        for k, words in enumerate(lines))  # fmt: skip
        out.append(
            f'<g data-transition="{" ".join(sorted(ways))}" data-node="{node_id}">'
            f'<rect x="{x - 1.6:.2f}" y="{y - 1.6:.2f}" width="3.2" height="3.2" rx="0.6" '
            f'fill="{CHANGE}"/><text x="{x:.2f}" y="{y + 0.75:.2f}" font-size="{FONT + 0.2}" '
            f'text-anchor="middle" fill="#fff" {SANS}>{glyph}</text>{texts}</g>'
        )

    # the products: a numbered marker on the shelf, and beside it what and where
    for number, node_id, sku in stops:
        x, y = at(node_id)
        p = services.catalogue.by_sku(sku)
        n = nodes[node_id]
        if n.node_type in ("counter", "cabinet"):  # not self-service: say where to ask (FR-12)
            place = f"{n.zone}, ask a colleague"
        else:
            place = ", ".join(s for s in (f"rack {n.rack}" if n.rack else "",
                                          _shelf(services, sku, node_id)) if s)  # fmt: skip
        words = f"{number}. {p.name if p else sku}" + (f" · {place}" if place else "")
        size = SMALL + 0.1
        lx, ly = labels.place(x - MARKER_R, y + MARKER_R + size + 0.1, words, size,
                              lo=left + 0.6, hi=right - 0.6)  # fmt: skip
        out.append(
            f'<g data-stop="{number}" data-node="{node_id}">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{MARKER_R}" fill="{STOP}" stroke="#fff" '
            f'stroke-width="0.4"/><text x="{x:.2f}" y="{y + 0.7:.2f}" font-size="{FONT}" '
            f'font-weight="700" text-anchor="middle" fill="#fff" {SANS}>{number}</text>'
            + _text(lx, ly, words, size=size, weight=700, fill=STOP)
            + "</g>"
        )

    # a key, in words, for the marks that are not words
    ky = x_max + pad_b - 4.8
    k = left + 1.2
    out.append(
        f'<line x1="{k:.2f}" y1="{ky - 0.6:.2f}" x2="{k + 3:.2f}" y2="{ky - 0.6:.2f}" '
        f'stroke="{ROUTE}" stroke-width="0.9"/>' + _text(k + 3.6, ky, "your route", size=SMALL, fill=MUTED)
        + f'<circle cx="{k + 15.4:.2f}" cy="{ky - 0.6:.2f}" r="1" fill="{STOP}"/>'
        + _text(k + 16.8, ky, "pick up, in this order", size=SMALL, fill=MUTED)
        + f'<rect x="{k:.2f}" y="{ky + 1.4:.2f}" width="2.2" height="2.2" rx="0.4" fill="{SERVICE}" '
        f'stroke="{MUTED}" stroke-width="0.2"/>'
        + _text(k + 3.6, ky + 3.2, "counter or locked cabinet: ask a colleague", size=SMALL, fill=MUTED)
    )  # fmt: skip
    out.append("</svg>")
    return "".join(out)
