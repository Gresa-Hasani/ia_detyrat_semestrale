"""Readable, depth-limited renderings of a search tree (text and Mermaid).

Large trees are never drawn in full: only nodes up to ``max_depth`` and at
most ``max_nodes`` nodes are shown, and every rendering states that it is a
partial view of the complete tree.
"""

from __future__ import annotations

from typing import Callable

from .core import DEAD_END, DEPTH_LIMIT, DUPLICATE, EXPANDED, FRONTIER, GOAL, INVALID, SearchTree

STATUS_MARK = {
    GOAL: "GOAL",
    DUPLICATE: "duplicate",
    INVALID: "invalid",
    DEPTH_LIMIT: "depth limit",
    FRONTIER: "not expanded",
    DEAD_END: "dead end",
    EXPANDED: "",
}


def _visible_nodes(tree: SearchTree, max_depth: int, max_nodes: int) -> list[int]:
    """Breadth-first selection of the nodes to draw (solution path first)."""
    on_path = {n.id for n in tree.solution_path() if n.depth <= max_depth}
    chosen: list[int] = []
    seen: set[int] = set()
    queue = [0]
    while queue:
        node_id = queue.pop(0)
        node = tree.nodes[node_id]
        if node.depth > max_depth:
            continue
        if len(chosen) >= max_nodes and node_id not in on_path:
            continue
        chosen.append(node_id)
        seen.add(node_id)
        queue.extend(node.children)
    return [i for i in chosen if tree.nodes[i].parent is None or tree.nodes[i].parent in seen]


def _hidden_count(tree: SearchTree, shown: set[int]) -> int:
    return len(tree.nodes) - len(shown)


def render_text(tree: SearchTree, format_state: Callable, max_depth: int = 3,
                max_nodes: int = 60) -> str:
    """Indented text tree: ``[id] action -> state (status)``."""
    shown_list = _visible_nodes(tree, max_depth, max_nodes)
    shown = set(shown_list)
    on_path = {n.id for n in tree.solution_path()}
    lines: list[str] = []

    def walk(node_id: int, prefix: str, last: bool) -> None:
        node = tree.nodes[node_id]
        connector = "" if node.parent is None else ("`-- " if last else "|-- ")
        action = "" if node.action is None else f"{node.action} -> "
        state = format_state(node.state) if node.state is not None else "(no state)"
        notes = [STATUS_MARK[node.status]] if STATUS_MARK[node.status] else []
        if node.reason:
            notes.append(node.reason)
        if node.id in on_path and node.status != GOAL:
            notes.append("on solution path")
        if node.id == 0:
            notes.insert(0, "INITIAL")
        note = f"  ({'; '.join(notes)})" if notes else ""
        lines.append(f"{prefix}{connector}[{node.id}] d={node.depth} {action}{state}{note}")
        kids = [c for c in node.children if c in shown]
        child_prefix = prefix + ("" if node.parent is None else ("    " if last else "|   "))
        for i, child in enumerate(kids):
            walk(child, child_prefix, i == len(kids) - 1)

    walk(0, "", True)
    hidden = _hidden_count(tree, shown)
    lines.append(
        f"(Partial view: {len(shown)} of {len(tree.nodes)} nodes, depth <= {max_depth}; "
        f"{hidden} nodes not shown.)" if hidden else
        f"(Complete tree: {len(tree.nodes)} nodes.)"
    )
    return "\n".join(lines)


def _mermaid_escape(text: str) -> str:
    return text.replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")


def render_mermaid(tree: SearchTree, format_label: Callable, max_depth: int = 3,
                   max_nodes: int = 40, title: str | None = None) -> str:
    """Mermaid flowchart (top-down). ``format_label`` may return lines joined by ``<br/>``."""
    shown_list = _visible_nodes(tree, max_depth, max_nodes)
    shown = set(shown_list)
    on_path = {n.id for n in tree.solution_path()}
    lines = ["flowchart TD"] + ([f"    %% {title}"] if title else [])
    for node_id in shown_list:
        node = tree.nodes[node_id]
        label = format_label(node.state) if node.state is not None else "no state"
        label = "<br/>".join(_mermaid_escape(part) for part in label.split("<br/>"))
        tag = "START" if node.id == 0 else STATUS_MARK[node.status]
        header = f"id {node.id}, d={node.depth}" + (f", {tag}" if tag else "")
        lines.append(f'    n{node.id}["{header}<br/>{label}"]')
    for node_id in shown_list:
        node = tree.nodes[node_id]
        if node.parent is not None and node.parent in shown:
            lines.append(f'    n{node.parent} -->|"{_mermaid_escape(node.action)}"| n{node.id}')
    hidden = _hidden_count(tree, shown)
    if hidden:
        note = f"Partial tree: {len(shown)} of {len(tree.nodes)} nodes shown (depth at most {max_depth})"
        lines.append(f'    partialNote["{note}"]')
        lines.append("    class partialNote note")
    lines += [
        "    classDef start fill:#dbeafe,stroke:#1d4ed8,color:#111",
        "    classDef goal fill:#dcfce7,stroke:#15803d,color:#111",
        "    classDef path stroke:#15803d,stroke-width:3px",
        "    classDef duplicate fill:#f3f4f6,stroke:#9ca3af,color:#555,stroke-dasharray:4 3",
        "    classDef invalid fill:#fee2e2,stroke:#b91c1c,color:#111",
        "    classDef cut fill:#fef9c3,stroke:#a16207,color:#111",
        "    classDef note fill:#ffffff,stroke:#ffffff,color:#555",
    ]
    for node_id in shown_list:
        node = tree.nodes[node_id]
        classes = []
        if node.id == 0:
            classes.append("start")
        elif node.status == GOAL:
            classes.append("goal")
        elif node.status == DUPLICATE:
            classes.append("duplicate")
        elif node.status == INVALID:
            classes.append("invalid")
        elif node.status in (DEPTH_LIMIT, FRONTIER):
            classes.append("cut")
        if node.id in on_path and node.id != 0 and node.status != GOAL:
            classes.append("path")
        for css_class in classes:
            lines.append(f"    class n{node.id} {css_class}")
    return "\n".join(lines)
