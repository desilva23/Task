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

CROWDED: list[str] = []  # labels that found no clear place — a test keeps this empty

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
    picks: tuple[tuple[int, str, str, str], ...] = ()  # (number, node, product, where) — tap a pin


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
        picks = tuple((n, node, _label(services, sku), _where(services, sku, node))
                      for n, node, sku in my_stops)  # fmt: skip
        plates.append(Plate(level, name, svg, mine, tuple((n, node) for n, node, _ in my_stops),
                            picks))  # fmt: skip
    return plates


# ── drawing ──────────────────────────────────────────────────────────────────────────────────


def _text(x, y, words, size=None, anchor="start", weight=400, fill=None, extra=""):
    size, fill = size or FONT, fill or INK
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" {SANS} {HALO} {extra}>{escape(words)}</text>')  # fmt: skip


def _width(words: str, size: float) -> float:
    return (
        len(words) * size * 0.58 + 0.8
    )  # measured 0.46–0.64 per letter in Chromium; plus a margin


def _shelf(services, sku: str, node_id: str) -> str:
    for p in services.planogram.for_sku(sku):
        if p.node_id == node_id and p.shelf_no:
            return f"shelf {p.shelf_no}"
    return ""


def _label(services, sku: str) -> str:
    p = services.catalogue.by_sku(sku)
    return f"{p.name} {p.size}" if p else sku


def _where(services, sku: str, node_id: str) -> str:
    """Where to put your hand on it, in words: aisle, rack and shelf — or the counter to ask at."""
    n = services.store.nodes[node_id]
    if n.node_type in ("counter", "cabinet"):  # not self-service (FR-12)
        return f"{n.zone} — ask a colleague"
    parts = [f"Aisle {n.aisle}" if n.aisle else "", f"rack {n.rack}" if n.rack else "",
             _shelf(services, sku, node_id)]  # fmt: skip
    return ", ".join(s for s in parts if s)


class _Layout:
    """Everything drawn occupies a rectangle; a label goes in the first of its candidate places
    that touches nothing — no shelf, box, pin or other label. The route line may pass under a
    label: every label has a halo."""

    def __init__(self, left: float, right: float):
        self.rects: list[tuple[float, float, float, float]] = []  # left, top, right, bottom
        self.left, self.right = left + 0.6, right - 0.6  # and nothing runs off the edge

    def block(self, left, top, right, bottom):
        self.rects.append((left, top, right, bottom))

    def _rect(self, x, y, words, size, anchor):
        span = _width(words, size)
        left = x - span if anchor == "end" else x - span / 2 if anchor == "middle" else x
        return left, y - size * 0.82, left + span, y + size * 0.22

    def free(self, rect) -> bool:
        l1, t1, r1, b1 = rect
        if l1 < self.left or r1 > self.right:
            return False
        return not any(l1 < r2 and l2 < r1 and t1 < b2 and t2 < b1 for l2, t2, r2, b2 in self.rects)

    def first_free(self, candidates, words, size):
        for x, y, anchor in candidates:
            rect = self._rect(x, y, words, size, anchor)
            if self.free(rect):
                self.block(*rect)
                return x, y, anchor
        return None

    def place(self, candidates, words, size):
        """``candidates``: (x, y, anchor) in order of preference. Returns the one used."""
        found = self.first_free(candidates, words, size)
        if found:
            return found
        CROWDED.append(words)
        x, y, anchor = candidates[0]  # nowhere is clear: the first choice, kept inside the edges
        l1, _, r1, _ = self._rect(x, y, words, size, anchor)
        x += max(0.0, self.left - l1) - max(0.0, r1 - self.right)
        self.block(*self._rect(x, y, words, size, anchor))
        return x, y, anchor


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

    # floor changes, as short lines: the rear core's above the plan, the front core's below it
    events: dict[str, list[str]] = {}
    for node_id, way, words in marks:
        events.setdefault(node_id, []).append(("↑ " if way == "up" else "↓ ") + words)
    rear = {k: v for k, v in events.items() if at(k)[1] < x_max / 2}
    front = {k: v for k, v in events.items() if at(k)[1] >= x_max / 2}
    line = FONT + 0.6
    item = 2 * line + 0.6  # a product in the list: its name, then where it is
    pad_t = 8.5 + sum(len(v) for v in rear.values()) * line
    list_top = x_max + 4.5 + sum(len(v) for v in front.values()) * line
    pad_b = (list_top - x_max) + (2.6 + len(stops) * item if stops else 0) + 7.5
    left, top = y_min - PAD_L, -pad_t
    w, h = (y_max - y_min) + PAD_L + PAD_R, x_max + pad_t + pad_b
    right = left + w
    lay = _Layout(left, right)
    out = [
        f'<svg data-floor="{level}" viewBox="{left:.1f} {top:.1f} {w:.1f} {h:.1f}" width="100%" '
        f'style="display:block;max-width:100%;height:auto" role="img" '
        f'aria-label="Floor {level} map. The directions list above describes the same route.">',
        f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" fill="{FLOOR_BG}"/>',
        _text(left + 1.2, top + 3.0, f"Floor {level} · {floor_name}", size=2.4, weight=700),
        _text(left + 1.2, top + 5.9, "◀ rear of store", size=SMALL, fill=MUTED),
        _text(right - 1.2, top + 5.9, "front of store ▶", size=SMALL, anchor="end", fill=MUTED),
    ]
    labels: list[str] = []  # drawn after the route, so the words sit on top

    # 1. everything solid, each blocking its rectangle
    aisles: dict[int, list] = {}
    for node_id, n in here.items():
        if n.node_type in ("aisle_end", "rack"):
            aisles.setdefault(n.aisle, []).append(node_id)
    bars = []
    for aisle, ids in sorted(aisles.items()):
        pts = sorted(at(i) for i in ids)
        (x1, y), (x2, _) = pts[0], pts[-1]
        zone = next((here[i].zone for i in ids if here[i].node_type == "rack"), "") or ""
        bars.append((aisle, zone, x1, x2, y))
        out.append(f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" stroke="{SHELF}" '
                   f'stroke-width="{AISLE_W}" stroke-linecap="round"/>')  # fmt: skip
        lay.block(x1 - AISLE_W / 2, y - AISLE_W / 2, x2 + AISLE_W / 2, y + AISLE_W / 2)

    def box(x, y, r):
        lay.block(x - r, y - r, x + r, y + r)

    tills = sorted((at(i) for i, n in here.items() if n.node_type == "till"), key=lambda p: p[1])
    for x, y in tills:
        out.append(f'<rect x="{x - 1:.2f}" y="{y - 1.2:.2f}" width="2" height="2.4" rx="0.4" '
                   f'fill="{SERVICE}" stroke="{MUTED}" stroke-width="0.2"/>')  # fmt: skip
        box(x, y, 1.2)
    cores = []
    for node_id, n in here.items():
        x, y = at(node_id)
        if n.node_type in ("counter", "cabinet"):
            words = n.zone.removesuffix(" Counter") + (
                " (locked)" if n.node_type == "cabinet" else ""
            )
            out.append(f'<rect x="{x - 1.2:.2f}" y="{y - 1.2:.2f}" width="2.4" height="2.4" '
                       f'rx="0.4" fill="{SERVICE}" stroke="{MUTED}" stroke-width="0.2"/>')  # fmt: skip
            box(x, y, 1.2)
            # along the rear wall, upright, so the name never crosses an aisle
            out.append(_text(x - 1.8, y, words, size=SMALL, anchor="middle", weight=700,
                             extra=f'transform="rotate(-90 {x - 1.8:.2f} {y:.2f})"'))  # fmt: skip
            span = _width(words, SMALL) / 2
            lay.block(x - 1.8 - SMALL, y - span, x - 1.8 + 0.4, y + span)
        elif n.node_type == "entrance":
            out.append(f'<path d="M{x + 2.4:.2f} {y - 1.4:.2f} l-2 1.4 l2 1.4" fill="none" '
                       f'stroke="{INK}" stroke-width="0.5"/>')  # fmt: skip
            lay.block(x, y - 1.6, x + 2.8, y + 1.6)
            labels.append(("Entrance", [(x, y + 3.6, "middle"), (x + 3.2, y + 0.7, "start"),
                                        (x, y - 2.4, "middle"), (x - 2.0, y + 3.6, "end")],
                           FONT, 700, INK))  # fmt: skip
        elif n.node_type == "core":
            cores.append(node_id)
            out.append(f'<rect x="{x - 1.4:.2f}" y="{y - 1.4:.2f}" width="2.8" height="2.8" '
                       f'rx="0.5" fill="#fff" stroke="{CHANGE}" stroke-width="0.35"/>'
                       f'<text x="{x:.2f}" y="{y + 0.7:.2f}" font-size="{FONT}" text-anchor="middle" '
                       f'fill="{CHANGE}" {SANS}>⇅</text>')  # fmt: skip
            box(x, y, 1.7)
            side = [(x - 2.4, y + 0.7, "end"), (x + 2.4, y + 0.7, "start")]
            labels.append(("Stairs & lift", side if x > mid_y else side[::-1], SMALL, 700, CHANGE))
    if tills:
        tx, ty = tills[0]
        labels.append(("Checkouts", [(tx - 1.2, ty - 2.0, "start"), (tx + 1.6, ty + 0.7, "start"),
                                     (tx - 1.6, ty + 0.7, "end")], FONT, 700, INK))  # fmt: skip

    for seg in segments:
        pts = " ".join(f"{at(i)[0]:.2f},{at(i)[1]:.2f}" for i in seg.nodes)
        out.append(f'<polyline data-route="{" ".join(seg.nodes)}" points="{pts}" fill="none" '
                   f'stroke="{ROUTE}" stroke-width="0.9" stroke-linejoin="round" '
                   'stroke-linecap="round" opacity="0.9"/>')  # fmt: skip

    def around(x, y, gap):  # right, left, below, above
        return [(x + gap, y + 0.7, "start"), (x - gap, y + 0.7, "end"),
                (x, y + gap + FONT, "middle"), (x, y - gap - 0.4, "middle")]  # fmt: skip

    if nodes[start].level == level:
        x, y = at(start)
        out.append(f'<g data-start="{start}"><circle cx="{x:.2f}" cy="{y:.2f}" r="1.3" '
                   f'fill="{INK}" stroke="#fff" stroke-width="0.4"/></g>')  # fmt: skip
        box(x, y, 1.4)
        gap = 3.2 if nodes[start].node_type == "entrance" else 2.0  # clear of the door mark
        labels.append((("Start here", "Start"), around(x, y, gap), FONT, 700, INK))
    if route.get("till") and nodes[route["till"]].level == level:
        x, y = at(route["till"])
        out.append(f'<g data-till="{route["till"]}"><circle cx="{x:.2f}" cy="{y:.2f}" r="1.4" '
                   f'fill="{INK}" stroke="#fff" stroke-width="0.4"/></g>')  # fmt: skip
        box(x, y, 1.5)
        labels.append(("Pay here", around(x, y, 2.0), FONT, 700, INK))

    for node_id in events:
        x, y = at(node_id)
        ways = {m[1] for m in marks if m[0] == node_id}
        glyph = "⇅" if len(ways) > 1 else ("↑" if "up" in ways else "↓")
        out.append(
            f'<g data-transition="{" ".join(sorted(ways))}" data-node="{node_id}">'
            f'<rect x="{x - 1.6:.2f}" y="{y - 1.6:.2f}" width="3.2" height="3.2" rx="0.6" '
            f'fill="{CHANGE}"/><text x="{x:.2f}" y="{y + 0.75:.2f}" font-size="{FONT + 0.2}" '
            f'text-anchor="middle" fill="#fff" {SANS}>{glyph}</text></g>'
        )
        box(x, y, 1.8)

    for number, node_id, _ in stops:  # the pins: big, numbered, and named in the list below
        x, y = at(node_id)
        out.append(
            f'<g data-stop="{number}" data-node="{node_id}">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{MARKER_R}" fill="{STOP}" stroke="#fff" '
            f'stroke-width="0.4"/><text x="{x:.2f}" y="{y + 0.7:.2f}" font-size="{FONT}" '
            f'font-weight="700" text-anchor="middle" fill="#fff" {SANS}>{number}</text></g>'
        )
        box(x, y, MARKER_R + 0.2)

    # 2. the words, each in the first place where it touches nothing
    for aisle, zone, x1, _, y in bars:
        # always above its own shelf — below would sit as close to the next aisle as to this one
        above = y - AISLE_W / 2 - 0.45
        cands = [(x1 + 1.2 + k * 3.0, above, "start") for k in range(6)]
        options = (f"Aisle {aisle} · {zone}", f"{aisle} · {zone}", f"Aisle {aisle}", str(aisle))
        for option in options:
            found = lay.first_free(cands, option, SMALL)
            if found:
                break
        else:
            option = options[-1]
            found = lay.place(cands, option, SMALL)  # records it in CROWDED
        x, ly, _ = found
        out.append(_text(x, ly, option, size=SMALL, fill="#3d4440", weight=600,
                         extra=f'data-aisle="{aisle}"'))  # fmt: skip
    for words, cands, size, weight, fill in labels:
        options = words if isinstance(words, tuple) else (words,)  # longest first, then shorter
        for option in options:
            found = lay.first_free(cands, option, size)
            if found:
                break
        else:
            option = options[-1]
            found = lay.place(cands, option, size)  # records it in CROWDED
        x, y, anchor = found
        out.append(_text(x, y, option, size=size, anchor=anchor, weight=weight, fill=fill))

    # 3. below the plan: floor changes at the front core, the products on this floor, the key
    for lines in rear.values():
        out.append("".join(_text(left + 1.2, top + 8.2 + FONT + k * line, words, weight=700,
                                 fill=CHANGE) for k, words in enumerate(lines)))  # fmt: skip
    for lines in front.values():
        out.append("".join(_text(right - 1.2, x_max + 3.4 + FONT + k * line, words, anchor="end",
                                 weight=700, fill=CHANGE) for k, words in enumerate(lines)))  # fmt: skip
    y = list_top
    if stops:
        out.append(f'<line x1="{left + 1.2:.2f}" y1="{y:.2f}" x2="{right - 1.2:.2f}" y2="{y:.2f}" '
                   f'stroke="{SHELF}" stroke-width="0.25"/>')  # fmt: skip
        out.append(_text(left + 1.2, y + 2.6, "Pick up on this floor", size=SMALL, weight=700,
                         fill=MUTED))  # fmt: skip
        y += 2.6
        for number, node_id, sku in stops:
            cy = y + 1.2 + FONT * 0.7
            out.append(
                f'<g data-pick="{number}"><circle cx="{left + 2.6:.2f}" cy="{cy:.2f}" r="1.35" '
                f'fill="{STOP}"/><text x="{left + 2.6:.2f}" y="{cy + 0.6:.2f}" '
                f'font-size="{SMALL}" font-weight="700" text-anchor="middle" fill="#fff" {SANS}>'
                f"{number}</text>"
                + _text(left + 4.8, cy + 0.6, _label(services, sku), weight=700)
                + _text(left + 4.8, cy + 0.6 + line, _where(services, sku, node_id),
                        size=SMALL, fill=MUTED)
                + "</g>"
            )  # fmt: skip
            y += item

    ky = top + h - 4.6
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
