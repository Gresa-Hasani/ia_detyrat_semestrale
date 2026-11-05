"""Graphical search-tree diagrams: SVG (pure Python), PNG (Pillow, optional), DOT.

The nodes and edges are exactly those of the tree built by the search
(``core.build_search_tree``). What is drawn follows ``visualization``: all
nodes up to a depth, the complete solution path with the alternatives at each
of its steps, and a marker for every omitted branch. A problem may also hide
its duplicate leaves (repeated states); the caption then says so.

Every problem describes the look of its nodes with a ``DiagramStyle``:

* ``grid`` nodes draw the state as a table of cells (8-Puzzle board,
  workforce schedule) with per-value cell colours;
* ``ellipse`` nodes draw a short text label (Missionaries and Cannibals
  ``[m, c, b]``).

Node status is shown by the fill and frame colour (processed, goal,
killed/invalid, no new child, repeated, not expanded, omitted); a numbered
circle gives the order in which the search expanded the node; thick green
arrows mark the solution path; the ruler on the left gives the depth.

Layout: hierarchical, top-down, contour-based tidy tree (in the spirit of
Reingold and Tilford), so boxes never overlap and a deep solution path does
not widen the drawing. SVG and DOT need only the standard library; PNG uses
Pillow when it is installed.
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from xml.sax.saxutils import escape

from .core import DEAD_END, DEPTH_LIMIT, DUPLICATE, FRONTIER, GOAL, INVALID, SearchTree, TreeNode
from .visualization import _more, _subtree_size, _visible_nodes

# ------------------------------------------------------------------ geometry
FONT = 12
CHAR_W = 7.3             # width of a monospace character at FONT px
LINE_H = 15
CELL = 18                # side of one grid cell
FRAME = 5                # coloured frame around a grid
ELLIPSE_H = 34
H_GAP, V_GAP = 22, 50
MARGIN, RULER = 18, 64
BADGE_R = 9

# kind -> (fill, stroke, dashed, legend text)
KINDS = {
    "start": ("#bbf7d0", "#1d4ed8", False, "initial state (processed)"),
    "normal": ("#bbf7d0", "#15803d", False, "processed node (expanded)"),
    "goal": ("#facc15", "#a16207", False, "goal node"),
    "invalid": ("#f87171", "#b91c1c", False, "killed node (constraint violated)"),
    "dead": ("#e0f2fe", "#475569", False, "no new child possible"),
    "duplicate": ("#f1f5f9", "#94a3b8", True, "repeated state (already generated)"),
    "cut": ("#ffffff", "#64748b", False, "generated, not expanded"),
    "omitted": ("#ffffff", "#94a3b8", True, "omitted branch (not drawn)"),
}
KIND_ORDER = ("start", "normal", "goal", "invalid", "dead", "duplicate", "cut", "omitted")
PATH_COLOR = "#15803d"
EDGE_COLOR = "#334155"
BADGE_COLOR = "#ea580c"


@dataclass(frozen=True)
class NodeView:
    """How one state is drawn."""

    shape: str                                      # "grid" or "ellipse"
    grid: tuple[tuple[str, ...], ...] = ()
    text: str = ""
    cell_styles: dict[str, tuple[str, str]] = field(default_factory=dict)   # value -> (fill, ink)


def _same(action: str) -> str:
    return action


def _no_caption(node: TreeNode) -> str:
    return ""


@dataclass(frozen=True)
class DiagramStyle:
    """Problem-specific look of a diagram."""

    title: str
    view: Callable[[object], NodeView]
    edge_label: Callable[[str], str] = _same
    caption: Callable[[TreeNode], str] = _no_caption
    notes: tuple[str, ...] = ()                          # notation explained in the legend
    cell_legend: tuple[tuple[str, str, str, str], ...] = ()   # (fill, ink, value, meaning)
    hide_duplicates: bool = False


def _kind(tree: SearchTree, node_id: int) -> str:
    status = tree.nodes[node_id].status
    if status == GOAL:
        return "goal"
    if node_id == 0:
        return "start"
    return {INVALID: "invalid", DUPLICATE: "duplicate", FRONTIER: "cut", DEPTH_LIMIT: "cut",
            DEAD_END: "dead"}.get(status, "normal")


@dataclass
class Box:
    """One drawn node: a search-tree node or an omitted-branch marker."""

    key: str
    depth: int
    kind: str
    node_id: int | None = None
    view: NodeView | None = None
    label: list[str] = field(default_factory=list)    # text of an omitted marker
    caption: str = ""
    badge: int | None = None
    on_path: bool = False
    edge_label: str = ""
    parent: str | None = None
    children: list["Box"] = field(default_factory=list)
    x: float = 0.0          # centre
    y: float = 0.0          # top
    slot: float = 0.0       # horizontal offset of the centre from the parent's centre

    @property
    def body_width(self) -> float:
        if self.view is None:
            return max(len(line) for line in self.label) * CHAR_W + 16
        if self.view.shape == "grid":
            return len(self.view.grid[0]) * CELL + 2 * FRAME
        return len(self.view.text) * CHAR_W + 34

    @property
    def body_height(self) -> float:
        if self.view is None:
            return len(self.label) * LINE_H + 12
        if self.view.shape == "grid":
            return len(self.view.grid) * CELL + 2 * FRAME
        return ELLIPSE_H

    @property
    def width(self) -> float:
        return max(self.body_width, len(self.caption) * CHAR_W * 0.92 + 4)

    @property
    def height(self) -> float:
        return self.body_height + (LINE_H + 2 if self.caption else 0)


@dataclass
class TreeDrawing:
    """A laid-out drawing; sizes are in pixels."""

    style: DiagramStyle
    caption: list[str]
    legend: list[tuple[str, str]]
    root: Box
    boxes: list[Box]
    width: float
    height: float
    legend_top: float
    legend_height: float
    level_top: dict[int, float]
    level_bottom: dict[int, float]
    complete: bool
    hidden_duplicates: int

    def edges(self) -> list[tuple[Box, Box]]:
        return [(b, c) for b in self.boxes for c in b.children]


def _tidy_layout(box: Box) -> dict[int, tuple[float, float]]:
    """Contour-based tidy tree layout; stores each child's offset in ``slot``."""
    contour = {box.depth: (-box.width / 2, box.width / 2)}
    if not box.children:
        return contour
    placed: list[tuple[Box, float]] = []
    merged: dict[int, tuple[float, float]] = {}
    for child in box.children:
        child_contour = _tidy_layout(child)
        shift = 0.0
        if placed:
            shift = max(merged[d][1] - child_contour[d][0] + H_GAP for d in child_contour if d in merged)
        placed.append((child, shift))
        for d, (lo, hi) in child_contour.items():
            lo, hi = lo + shift, hi + shift
            merged[d] = (min(merged[d][0], lo), max(merged[d][1], hi)) if d in merged else (lo, hi)
    centre = (placed[0][1] + placed[-1][1]) / 2
    for child, shift in placed:
        child.slot = shift - centre
    for d, (lo, hi) in merged.items():
        lo, hi = lo - centre, hi - centre
        contour[d] = (min(contour[d][0], lo), max(contour[d][1], hi)) if d in contour else (lo, hi)
    return contour


def build_drawing(tree: SearchTree, style: DiagramStyle, max_depth: int = 2, max_nodes: int = 40,
                  include_solution_path: bool = True) -> TreeDrawing:
    """Select the nodes to draw (from the real tree) and compute the layout."""
    shown_ids = _visible_nodes(tree, max_depth, max_nodes, include_solution_path)
    hidden_dups = 0
    if style.hide_duplicates:
        shown_ids = [i for i in shown_ids if tree.nodes[i].status != DUPLICATE]
        hidden_dups = sum(1 for n in tree.nodes if n.status == DUPLICATE)
    shown = set(shown_ids)
    on_path = {n.id for n in tree.solution_path()}

    boxes: dict[str, Box] = {}
    for node_id in shown_ids:
        node = tree.nodes[node_id]
        boxes[f"n{node_id}"] = Box(
            key=f"n{node_id}", depth=node.depth, kind=_kind(tree, node_id), node_id=node_id,
            view=style.view(node.state), caption=style.caption(node), badge=node.order,
            on_path=node_id in on_path, edge_label=style.edge_label(node.action) if node.action else "",
            parent=None if node.parent is None else f"n{node.parent}",
        )
    omitted_total = 0
    for node_id in shown_ids:
        hidden = sum(
            _subtree_size(tree, c) for c in tree.nodes[node_id].children
            if c not in shown and not (style.hide_duplicates and tree.nodes[c].status == DUPLICATE)
        )
        if hidden:
            omitted_total += hidden
            key = f"more{node_id}"
            boxes[key] = Box(key=key, depth=tree.nodes[node_id].depth + 1, kind="omitted",
                             label=textwrap.wrap(_more(hidden).replace("... ", ""), 16), parent=f"n{node_id}")
    for box in boxes.values():
        if box.parent:
            boxes[box.parent].children.append(box)
    root = boxes["n0"]
    contours = _tidy_layout(root)

    drawn = len(shown_ids)
    goal = tree.goal
    caption = [style.title]
    if omitted_total == 0 and hidden_dups == 0:
        caption.append(f"Complete search tree: all {len(tree.nodes)} nodes drawn.")
    elif omitted_total == 0:
        caption.append(f"Complete search tree: {drawn} of {len(tree.nodes)} nodes drawn; the other "
                       f"{hidden_dups} are repeated-state leaves (duplicates), left out for readability.")
    else:
        scope = f"all nodes up to depth {max_depth}" + (
            " plus the whole solution path and its alternatives" if include_solution_path and goal else "")
        caption.append(f"Partial search tree: {drawn} of {len(tree.nodes)} nodes drawn ({scope}).")
        caption.append("Dashed boxes stand for branches that exist in the tree but are not drawn.")
    caption.append(f"{tree.strategy.upper()} search: {tree.stats.nodes_generated:,} nodes generated, "
                   f"{tree.stats.nodes_expanded:,} expanded, "
                   + (f"goal at depth {goal.depth}." if goal else "no goal found."))

    kinds = {b.kind for b in boxes.values()}
    legend = [(k, KINDS[k][3]) for k in KIND_ORDER if k in kinds]
    legend_top = MARGIN + len(caption) * 18 + 8
    rows = len(legend) + len(style.cell_legend) + len(style.notes) + 2      # + path and badge keys
    legend_height = rows * 20 + 30
    top = legend_top + legend_height + 34

    level_height: dict[int, float] = {}
    for box in boxes.values():
        level_height[box.depth] = max(level_height.get(box.depth, 0), box.height)
    level_top: dict[int, float] = {}
    for depth in sorted(level_height):
        level_top[depth] = top
        top += level_height[depth] + V_GAP
    level_bottom = {d: level_top[d] + level_height[d] for d in level_top}

    left_edge = min(lo for lo, _ in contours.values())
    right_edge = max(hi for _, hi in contours.values())

    def place(box: Box, x: float) -> None:
        box.x, box.y = x, level_top[box.depth]
        for child in box.children:
            place(child, x + child.slot)

    place(root, MARGIN + RULER + BADGE_R - left_edge)
    longest = max(len(line) for line in caption + list(style.notes) + [text for _, text in legend])
    width = max(right_edge - left_edge + 2 * MARGIN + RULER + BADGE_R, longest * CHAR_W + 2 * MARGIN + 60, 640)
    complete = omitted_total == 0 and drawn + hidden_dups == len(tree.nodes)
    return TreeDrawing(style, caption, legend, root, list(boxes.values()), width, top - V_GAP + MARGIN,
                       legend_top, legend_height, level_top, level_bottom, complete, hidden_dups)


def _edge_points(drawing: TreeDrawing, parent: Box, child: Box) -> list[tuple[float, float]]:
    """Leave the parent vertically below its level, then go straight to the child."""
    y_low = drawing.level_bottom[parent.depth] + 6
    return [(parent.x, parent.y + parent.body_height), (parent.x, y_low), (child.x, child.y - 1)]


def _legend_items(drawing: TreeDrawing) -> list[tuple[str, tuple, str]]:
    """(type, payload, text) rows of the legend box, top to bottom."""
    items: list[tuple[str, tuple, str]] = [("kind", (k,), text) for k, text in drawing.legend]
    items += [("cell", (fill, ink, value), meaning) for fill, ink, value, meaning in drawing.style.cell_legend]
    items.append(("path", (), "solution path (thick green arrows)"))
    items.append(("badge", (), "number = order in which the search expanded the node"))
    items += [("note", (), note) for note in drawing.style.notes]
    return items


# ----------------------------------------------------------------------- SVG
def render_svg(drawing: TreeDrawing) -> str:
    w, h = drawing.width, drawing.height
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
        f'font-family="Consolas, \'DejaVu Sans Mono\', \'Courier New\', monospace" font-size="{FONT}">',
        f"<title>{escape(drawing.style.title)}</title>",
        "<defs>" + "".join(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" '
            f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{color}"/></marker>'
            for mid, color in (("arrow", EDGE_COLOR), ("arrow-path", PATH_COLOR))) + "</defs>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    y = MARGIN + 14
    for i, line in enumerate(drawing.caption):
        attrs = ' font-weight="bold" font-size="17" fill="#1e3a8a"' if i == 0 else ""
        out.append(f'<text x="{MARGIN}" y="{y}"{attrs}>{escape(line)}</text>')
        y += 18
    lt = drawing.legend_top
    out.append(f'<rect x="{MARGIN}" y="{lt:.0f}" width="{w - 2 * MARGIN:.0f}" height="{drawing.legend_height:.0f}" '
               f'fill="#ffffff" stroke="#b91c1c" stroke-width="1"/>')
    out.append(f'<text x="{MARGIN + 10}" y="{lt + 18:.0f}" font-weight="bold" fill="#1e3a8a">Legend</text>')
    for row, (kind, payload, text) in enumerate(_legend_items(drawing)):
        ly = lt + 40 + row * 20
        x = MARGIN + 14
        if kind == "kind":
            fill, stroke, dashed, _ = KINDS[payload[0]]
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            out.append(f'<rect x="{x}" y="{ly - 11}" width="26" height="15" rx="7" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="2"{dash}/>')
        elif kind == "cell":
            fill, ink, value = payload
            out.append(f'<rect x="{x + 5}" y="{ly - 12}" width="16" height="16" fill="{fill}" stroke="#64748b"/>')
            out.append(f'<text x="{x + 13}" y="{ly + 1}" text-anchor="middle" fill="{ink}">{escape(value)}</text>')
        elif kind == "path":
            out.append(f'<line x1="{x}" y1="{ly - 4}" x2="{x + 24}" y2="{ly - 4}" stroke="{PATH_COLOR}" '
                       f'stroke-width="3" marker-end="url(#arrow-path)"/>')
        elif kind == "badge":
            out.append(f'<circle cx="{x + 13}" cy="{ly - 4}" r="{BADGE_R}" fill="{BADGE_COLOR}"/>'
                       f'<text x="{x + 13}" y="{ly}" text-anchor="middle" fill="#ffffff" font-size="11">1</text>')
        indent = 10 if kind == "note" else 40
        out.append(f'<text x="{x + indent}" y="{ly}">{escape(text)}</text>')
    for depth, top in drawing.level_top.items():
        out.append(f'<text x="{MARGIN}" y="{top + 14}" fill="#64748b">depth {depth}</text>')
    for parent, child in drawing.edges():
        path = parent.on_path and child.on_path
        color, width = (PATH_COLOR, 3) if path else (EDGE_COLOR, 1.2)
        dash = ' stroke-dasharray="4 3"' if child.kind == "omitted" else ""
        points = _edge_points(drawing, parent, child)
        coords = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        out.append(f'<polyline id="edge-{parent.key}-{child.key}" points="{coords}" fill="none" stroke="{color}" '
                   f'stroke-width="{width}"{dash} marker-end="url(#{"arrow-path" if path else "arrow"})"/>')
        if child.edge_label:
            (x1, _), (_, y1), (x2, y2) = points
            lx, ly = x2 + (x1 - x2) * 0.25, y2 - (y2 - y1) * 0.3
            lw = len(child.edge_label) * CHAR_W + 6
            out.append(f'<rect x="{lx - lw / 2:.1f}" y="{ly - 11:.1f}" width="{lw:.1f}" height="15" fill="#ffffff"/>')
            out.append(f'<text x="{lx:.1f}" y="{ly + 1:.1f}" text-anchor="middle" font-size="11" '
                       f'fill="{color}">{escape(child.edge_label)}</text>')
    for box in drawing.boxes:
        out.extend(_svg_box(box))
    out.append("</svg>")
    return "\n".join(out)


def _frame(box: Box) -> tuple[str, str, bool, float]:
    fill, stroke, dashed, _ = KINDS[box.kind]
    if box.on_path and box.kind not in ("start", "goal"):
        stroke = PATH_COLOR
    width = 3 if box.kind in ("start", "goal") or box.on_path else 1.6
    return fill, stroke, dashed, width


def _svg_box(box: Box) -> list[str]:
    fill, stroke, dashed, stroke_w = _frame(box)
    dash = ' stroke-dasharray="5 3"' if dashed else ""
    bw, bh = box.body_width, box.body_height
    left, top = box.x - bw / 2, box.y
    out = [f'<g id="node-{box.key}" data-kind="{box.kind}">']
    view = box.view
    if view is None:                                            # omitted marker
        out.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="1.3"{dash}/>')
        for i, line in enumerate(box.label):
            out.append(f'<text x="{box.x:.1f}" y="{top + 18 + i * LINE_H:.1f}" text-anchor="middle" '
                       f'fill="#475569">{escape(line)}</text>')
    elif view.shape == "grid":
        out.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash}/>')
        for r, row in enumerate(view.grid):
            for c, value in enumerate(row):
                cfill, ink = view.cell_styles.get(value, ("#ffffff", "#000000"))
                cx, cy = left + FRAME + c * CELL, top + FRAME + r * CELL
                out.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CELL}" height="{CELL}" fill="{cfill}" '
                           f'stroke="#64748b" stroke-width="0.8"/>')
                if value.strip():
                    out.append(f'<text x="{cx + CELL / 2:.1f}" y="{cy + CELL / 2 + 4:.1f}" text-anchor="middle" '
                               f'fill="{ink}">{escape(value)}</text>')
    else:                                                       # ellipse
        out.append(f'<ellipse cx="{box.x:.1f}" cy="{top + bh / 2:.1f}" rx="{bw / 2:.1f}" ry="{bh / 2:.1f}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash}/>')
        out.append(f'<text x="{box.x:.1f}" y="{top + bh / 2 + 4:.1f}" text-anchor="middle">{escape(view.text)}</text>')
    if box.caption:
        out.append(f'<text x="{box.x:.1f}" y="{top + bh + LINE_H - 2:.1f}" text-anchor="middle" font-size="11" '
                   f'fill="#7f1d1d">{escape(box.caption)}</text>')
    if box.badge is not None:
        bx, by = left - 2, top - 2
        out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{BADGE_R}" fill="{BADGE_COLOR}"/>')
        out.append(f'<text x="{bx:.1f}" y="{by + 4:.1f}" text-anchor="middle" font-size="10" fill="#ffffff">'
                   f'{box.badge}</text>')
    out.append("</g>")
    return out


# ----------------------------------------------------------------------- PNG
def _font(size: int):
    from PIL import ImageFont
    for name in ("consola.ttf", "DejaVuSansMono.ttf", "cour.ttf", "LiberationMono-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_png(drawing: TreeDrawing, path: str | Path, scale: float = 2.0) -> bool:
    """Draw the same layout with Pillow. Returns False if Pillow is not installed."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    s = scale
    image = Image.new("RGB", (int(drawing.width * s), int(drawing.height * s)), "white")
    draw = ImageDraw.Draw(image)
    font, small, title_font = _font(int(FONT * s)), _font(int(10.5 * s)), _font(int(17 * s))

    def text(x, y, value, fnt=None, fill="#000000", anchor="ls"):
        draw.text((x * s, y * s), value, fill=fill, font=fnt or font, anchor=anchor)

    y = MARGIN + 14
    for i, line in enumerate(drawing.caption):
        text(MARGIN, y, line, title_font if i == 0 else font, "#1e3a8a" if i == 0 else "#000000")
        y += 18
    lt, w = drawing.legend_top, drawing.width
    draw.rectangle([MARGIN * s, lt * s, (w - MARGIN) * s, (lt + drawing.legend_height) * s],
                   outline="#b91c1c", width=int(s))
    text(MARGIN + 10, lt + 18, "Legend", fill="#1e3a8a")
    for row, (kind, payload, label) in enumerate(_legend_items(drawing)):
        ly = lt + 40 + row * 20
        x = MARGIN + 14
        if kind == "kind":
            fill, stroke, _, _ = KINDS[payload[0]]
            draw.rounded_rectangle([x * s, (ly - 11) * s, (x + 26) * s, (ly + 4) * s], 7 * s,
                                   fill=fill, outline=stroke, width=int(2 * s))
        elif kind == "cell":
            fill, ink, value = payload
            draw.rectangle([(x + 5) * s, (ly - 12) * s, (x + 21) * s, (ly + 4) * s], fill=fill, outline="#64748b")
            text(x + 13, ly - 4, value, fill=ink, anchor="mm")
        elif kind == "path":
            draw.line([x * s, (ly - 4) * s, (x + 24) * s, (ly - 4) * s], fill=PATH_COLOR, width=int(3 * s))
        elif kind == "badge":
            draw.ellipse([(x + 13 - BADGE_R) * s, (ly - 4 - BADGE_R) * s, (x + 13 + BADGE_R) * s,
                          (ly - 4 + BADGE_R) * s], fill=BADGE_COLOR)
            text(x + 13, ly - 4, "1", small, "#ffffff", "mm")
        text(x + (10 if kind == "note" else 40), ly, label)
    for depth, top in drawing.level_top.items():
        text(MARGIN, top + 14, f"depth {depth}", fill="#64748b")
    for parent, child in drawing.edges():
        on_path = parent.on_path and child.on_path
        color, width = (PATH_COLOR, 3) if on_path else (EDGE_COLOR, 1.2)
        points = _edge_points(drawing, parent, child)
        draw.line([(px * s, py * s) for px, py in points], fill=color, width=max(1, int(width * s)), joint="curve")
        (x1, y1), (x2, y2) = points[1], points[2]
        angle = math.atan2(y2 - y1, x2 - x1)
        head = [(x2, y2), (x2 - 9 * math.cos(angle - 0.4), y2 - 9 * math.sin(angle - 0.4)),
                (x2 - 9 * math.cos(angle + 0.4), y2 - 9 * math.sin(angle + 0.4))]
        draw.polygon([(px * s, py * s) for px, py in head], fill=color)
        if child.edge_label:
            lx, ly = x2 + (x1 - x2) * 0.25, y2 - (y2 - y1) * 0.3
            lw = len(child.edge_label) * CHAR_W + 6
            draw.rectangle([(lx - lw / 2) * s, (ly - 11) * s, (lx + lw / 2) * s, (ly + 4) * s], fill="#ffffff")
            text(lx, ly - 3, child.edge_label, small, color, "mm")
    for box in drawing.boxes:
        _png_box(draw, box, s, small, text)
    image.save(path)
    return True


def _png_box(draw, box: Box, s: float, small, text) -> None:
    fill, stroke, _, stroke_w = _frame(box)
    bw, bh = box.body_width, box.body_height
    left, top = box.x - bw / 2, box.y
    view = box.view
    if view is None:
        draw.rounded_rectangle([left * s, top * s, (left + bw) * s, (top + bh) * s], 5 * s, fill=fill,
                               outline=stroke, width=max(1, int(1.3 * s)))
        for i, line in enumerate(box.label):
            text(box.x, top + 18 + i * LINE_H, line, fill="#475569", anchor="ms")
    elif view.shape == "grid":
        draw.rounded_rectangle([left * s, top * s, (left + bw) * s, (top + bh) * s], 4 * s, fill=fill,
                               outline=stroke, width=max(1, int(stroke_w * s)))
        for r, row in enumerate(view.grid):
            for c, value in enumerate(row):
                cfill, ink = view.cell_styles.get(value, ("#ffffff", "#000000"))
                cx, cy = left + FRAME + c * CELL, top + FRAME + r * CELL
                draw.rectangle([cx * s, cy * s, (cx + CELL) * s, (cy + CELL) * s], fill=cfill, outline="#64748b")
                if value.strip():
                    text(cx + CELL / 2, cy + CELL / 2, value, fill=ink, anchor="mm")
    else:
        draw.ellipse([left * s, top * s, (left + bw) * s, (top + bh) * s], fill=fill, outline=stroke,
                     width=max(1, int(stroke_w * s)))
        text(box.x, top + bh / 2, view.text, anchor="mm")
    if box.caption:
        text(box.x, top + bh + LINE_H - 2, box.caption, small, "#7f1d1d", "ms")
    if box.badge is not None:
        bx, by = left - 2, top - 2
        draw.ellipse([(bx - BADGE_R) * s, (by - BADGE_R) * s, (bx + BADGE_R) * s, (by + BADGE_R) * s],
                     fill=BADGE_COLOR)
        text(bx, by, str(box.badge), small, "#ffffff", "mm")


# ----------------------------------------------------------------------- DOT
def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_dot(drawing: TreeDrawing) -> str:
    """Graphviz source of the same diagram (top-down, one rank per depth)."""
    lines = [
        "digraph SearchTree {",
        f'  label="{_dot_escape(" / ".join(drawing.caption))}"; labelloc=t; rankdir=TB;',
        '  node [fontname="Courier", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=10];',
    ]
    for box in drawing.boxes:
        fill, stroke, dashed, width = _frame(box)
        style = "filled,dashed" if dashed else "filled"
        badge = f"({box.badge}) " if box.badge is not None else ""
        if box.view is not None and box.view.shape == "grid":
            rows = "".join(
                "<TR>" + "".join(
                    f'<TD BGCOLOR="{box.view.cell_styles.get(v, ("#ffffff", "#000000"))[0]}">'
                    f'{escape(v) if v.strip() else " "}</TD>' for v in row) + "</TR>"
                for row in box.view.grid)
            extra = (f'<TR><TD COLSPAN="{len(box.view.grid[0])}">{escape(badge + box.caption)}</TD></TR>'
                     if badge or box.caption else "")
            label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">{rows}{extra}</TABLE>>'
            shape = "box"
        else:
            text = box.view.text if box.view is not None else " ".join(box.label)
            label = '"' + _dot_escape(badge + text) + (r"\n" + _dot_escape(box.caption) if box.caption else "") + '"'
            shape = "ellipse" if box.view is not None else "box"
        lines.append(f'  {box.key} [shape={shape}, label={label}, style="{style}", fillcolor="{fill}", '
                     f'color="{stroke}", penwidth={width}];')
    for parent, child in drawing.edges():
        path = parent.on_path and child.on_path
        attrs = [f'color="{PATH_COLOR if path else EDGE_COLOR}"', f"penwidth={3 if path else 1.0}"]
        if child.edge_label:
            attrs.append(f'label="{_dot_escape(child.edge_label)}"')
        if child.kind == "omitted":
            attrs.append("style=dashed")
        lines.append(f"  {parent.key} -> {child.key} [{', '.join(attrs)}];")
    for depth in sorted(drawing.level_top):
        same = " ".join(b.key for b in drawing.boxes if b.depth == depth)
        lines.append(f"  {{ rank=same; {same} }}")
    lines.append("}")
    return "\n".join(lines)


def export(tree: SearchTree, style: DiagramStyle, stem: str | Path, max_depth: int = 2, max_nodes: int = 40,
           include_solution_path: bool = True, png: bool = True) -> list[Path]:
    """Write ``stem``.svg, ``stem``.dot and (if Pillow is available) ``stem``.png."""
    drawing = build_drawing(tree, style, max_depth, max_nodes, include_solution_path)
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for suffix, content in ((".svg", render_svg(drawing)), (".dot", render_dot(drawing))):
        target = stem.with_suffix(suffix)
        target.write_text(content + "\n", encoding="utf-8", newline="\n")
        written.append(target)
    if png and render_png(drawing, stem.with_suffix(".png")):
        written.append(stem.with_suffix(".png"))
    return written
