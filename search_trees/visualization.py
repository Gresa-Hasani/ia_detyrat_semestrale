"""Readable, depth-limited renderings of a search tree (text and Mermaid).

Large trees are never drawn in full. A drawing contains

* every node up to ``max_depth`` (breadth-first, at most ``max_nodes``);
* the complete solution path from the root to the first goal, together with
  the direct children of every node on that path (the alternatives the
  search considered at each step), however deep the goal lies;
* for every drawn node whose children were not all drawn, a marker
  "... k more nodes not drawn", so an omitted branch is never mistaken for a
  leaf of the search tree.

Every rendering states whether it shows the complete tree or a partial view.
Nodes are always taken from the tree that the search actually built.
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


def _visible_nodes(tree: SearchTree, max_depth: int, max_nodes: int,
                   include_solution_path: bool = True) -> list[int]:
    """Ids of the nodes to draw, in breadth-first order (see module docstring)."""
    wanted: set[int] = set()
    queue = [0]
    while queue:                                     # depth-limited BFS selection
        node_id = queue.pop(0)
        node = tree.nodes[node_id]
        if node.depth > max_depth or len(wanted) >= max_nodes:
            continue
        wanted.add(node_id)
        queue.extend(node.children)
    if include_solution_path:
        for node in tree.solution_path():
            wanted.add(node.id)
            wanted.update(node.children)             # alternatives at every step
    # Keep only nodes whose parent is drawn, in breadth-first order.
    ordered, frontier = [], [0]
    while frontier:
        node_id = frontier.pop(0)
        if node_id not in wanted:
            continue
        ordered.append(node_id)
        frontier.extend(tree.nodes[node_id].children)
    return ordered


def _subtree_size(tree: SearchTree, node_id: int) -> int:
    size, stack = 0, [node_id]
    while stack:
        current = stack.pop()
        size += 1
        stack.extend(tree.nodes[current].children)
    return size


def _omitted(tree: SearchTree, shown: set[int]) -> dict[int, int]:
    """For every drawn node: number of descendants that are not drawn."""
    omitted = {}
    for node_id in shown:
        hidden = sum(_subtree_size(tree, c) for c in tree.nodes[node_id].children if c not in shown)
        if hidden:
            omitted[node_id] = hidden
    return omitted


def _more(count: int) -> str:
    return f"... {count} more node{'s' if count != 1 else ''} not drawn"


def _summary(tree: SearchTree, shown: set[int], max_depth: int, path: bool) -> str:
    if len(shown) == len(tree.nodes):
        return f"Complete tree: all {len(tree.nodes)} nodes shown"
    scope = f"depth at most {max_depth}" + (" plus the solution path" if path and tree.goal_ids else "")
    return f"Partial tree: {len(shown)} of {len(tree.nodes)} nodes shown ({scope})"


def render_text(tree: SearchTree, format_state: Callable, max_depth: int = 3,
                max_nodes: int = 60, include_solution_path: bool = True) -> str:
    """Indented text tree: ``[id] d=depth action -> state (status; reason)``."""
    shown_list = _visible_nodes(tree, max_depth, max_nodes, include_solution_path)
    shown = set(shown_list)
    omitted = _omitted(tree, shown)
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
            walk(child, child_prefix, i == len(kids) - 1 and node_id not in omitted)
        if node_id in omitted:
            lines.append(f"{child_prefix}`-- {_more(omitted[node_id])}")

    walk(0, "", True)
    lines.append(f"({_summary(tree, shown, max_depth, include_solution_path)}.)")
    return "\n".join(lines)


def _mermaid_escape(text: str) -> str:
    return text.replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")


def render_mermaid(tree: SearchTree, format_label: Callable, max_depth: int = 3,
                   max_nodes: int = 40, title: str | None = None,
                   include_solution_path: bool = True) -> str:
    """Mermaid flowchart (top-down). ``format_label`` may return lines joined by ``<br/>``."""
    shown_list = _visible_nodes(tree, max_depth, max_nodes, include_solution_path)
    shown = set(shown_list)
    omitted = _omitted(tree, shown)
    on_path = {n.id for n in tree.solution_path()}
    lines = ["flowchart TD"] + ([f"    %% {title}"] if title else [])
    for node_id in shown_list:
        node = tree.nodes[node_id]
        label = format_label(node.state) if node.state is not None else "no state"
        label = "<br/>".join(_mermaid_escape(part) for part in label.split("<br/>"))
        tag = "START" if node.id == 0 else STATUS_MARK[node.status]
        header = f"id {node.id}, d={node.depth}" + (f", {tag}" if tag else "")
        reason = f"<br/><i>{_mermaid_escape(node.reason)}</i>" if node.reason else ""
        lines.append(f'    n{node.id}["{header}<br/>{label}{reason}"]')
    for node_id in shown_list:
        node = tree.nodes[node_id]
        if node.parent is not None and node.parent in shown:
            lines.append(f'    n{node.parent} -->|"{_mermaid_escape(node.action)}"| n{node.id}')
    for node_id, count in omitted.items():
        lines.append(f'    more{node_id}["{_more(count)}"]')
        lines.append(f"    n{node_id} -.-> more{node_id}")
    lines.append(f'    summaryNote["{_summary(tree, shown, max_depth, include_solution_path)}"]')
    lines += [
        "    classDef start fill:#dbeafe,stroke:#1d4ed8,color:#111",
        "    classDef goal fill:#dcfce7,stroke:#15803d,color:#111",
        "    classDef path stroke:#15803d,stroke-width:3px",
        "    classDef duplicate fill:#f3f4f6,stroke:#9ca3af,color:#555,stroke-dasharray:4 3",
        "    classDef invalid fill:#fee2e2,stroke:#b91c1c,color:#111",
        "    classDef cut fill:#fef9c3,stroke:#a16207,color:#111",
        "    classDef omitted fill:#ffffff,stroke:#9ca3af,color:#555,stroke-dasharray:2 2",
        "    classDef note fill:#ffffff,stroke:#ffffff,color:#555",
        "    class summaryNote note",
    ]
    for node_id in omitted:
        lines.append(f"    class more{node_id} omitted")
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
