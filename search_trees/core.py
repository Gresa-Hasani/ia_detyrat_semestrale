"""Generic explicit search-tree construction shared by the three problems.

A *problem* supplies an initial state, a goal test and an ``expand`` function
that returns every transition from a state - valid ones and, where the
problem has them, invalid ones (for example unsafe river crossings) with the
reason they are invalid.

``build_search_tree`` grows an explicit tree from the initial state:

* every generated node gets an id, a parent id, the action on the edge to it
  and its depth, so parent-child relationships can be printed or drawn;
* the frontier is a FIFO queue (``bfs``) or a LIFO stack (``dfs``);
* duplicate detection (graph search): a state already generated at the same
  or a smaller depth becomes a *duplicate* leaf and is not expanded again;
* invalid transitions become *invalid* leaves (never expanded);
* nodes at ``max_depth`` are not expanded (*depth-limit* leaves).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Generic, Hashable, Protocol, TypeVar

S = TypeVar("S", bound=Hashable)

STRATEGIES = ("bfs", "dfs")

# Node statuses.
EXPANDED = "expanded"
GOAL = "goal"
FRONTIER = "frontier"         # generated but never expanded (search stopped)
DUPLICATE = "duplicate"
INVALID = "invalid"
DEPTH_LIMIT = "depth-limit"
DEAD_END = "dead-end"         # expanded, but no valid new child


class SearchTreeError(ValueError):
    """Raised for invalid problem definitions or search parameters."""


@dataclass(frozen=True)
class Transition(Generic[S]):
    """One possible move from a state."""

    action: str
    state: S | None            # None when the move does not produce a state
    valid: bool = True
    reason: str = ""           # why the transition is invalid


class Problem(Protocol[S]):
    """Interface every search-tree problem implements."""

    def initial_state(self) -> S: ...
    def is_goal(self, state: S) -> bool: ...
    def expand(self, state: S) -> list[Transition[S]]: ...
    def format_state(self, state: S) -> str: ...


@dataclass
class TreeNode(Generic[S]):
    """One node of the explicit search tree."""

    id: int
    state: S | None
    parent: int | None
    action: str | None
    depth: int
    status: str = FRONTIER
    reason: str = ""
    children: list[int] = field(default_factory=list)
    order: int | None = None   # 1-based position in the expansion sequence (None if never expanded)


@dataclass
class TreeStats:
    """Measured statistics of one tree construction."""

    nodes_generated: int = 0        # all tree nodes, including the root
    nodes_expanded: int = 0
    transitions_examined: int = 0   # valid + invalid transitions of expanded nodes
    valid_transitions: int = 0
    invalid_transitions: int = 0
    duplicates: int = 0
    depth_limit_leaves: int = 0
    dead_ends: int = 0
    unique_states: int = 0
    max_depth: int = 0              # deepest tree node of any status
    max_new_state_depth: int = 0    # deepest node holding a newly generated state
    max_frontier: int = 0
    goals_found: int = 0
    elapsed_seconds: float = 0.0
    limit_reached: str | None = None

    @property
    def raw_branching_factor(self) -> float:
        """Transitions (valid and invalid) per expanded node."""
        return self.transitions_examined / self.nodes_expanded if self.nodes_expanded else 0.0

    @property
    def valid_branching_factor(self) -> float:
        """Valid transitions per expanded node (duplicates included)."""
        return self.valid_transitions / self.nodes_expanded if self.nodes_expanded else 0.0

    @property
    def effective_branching_factor(self) -> float:
        """New (non-duplicate) children per expanded node."""
        if not self.nodes_expanded:
            return 0.0
        new_children = self.valid_transitions - self.duplicates
        return new_children / self.nodes_expanded


@dataclass
class SearchTree(Generic[S]):
    """All generated nodes plus statistics and the goal node ids."""

    nodes: list[TreeNode[S]]
    stats: TreeStats
    strategy: str
    goal_ids: list[int]

    @property
    def root(self) -> TreeNode[S]:
        return self.nodes[0]

    @property
    def goal(self) -> TreeNode[S] | None:
        return self.nodes[self.goal_ids[0]] if self.goal_ids else None

    def path_to(self, node_id: int) -> list[TreeNode[S]]:
        """Nodes from the root to ``node_id`` following parent links."""
        path = []
        current: int | None = node_id
        while current is not None:
            node = self.nodes[current]
            path.append(node)
            current = node.parent
        path.reverse()
        return path

    def solution_path(self) -> list[TreeNode[S]]:
        return self.path_to(self.goal_ids[0]) if self.goal_ids else []

    def solution_actions(self) -> list[str]:
        return [node.action for node in self.solution_path()[1:]]

    def solution_states(self) -> list[S]:
        return [node.state for node in self.solution_path()]


def _positive_or_none(name: str, value: object, minimum: int) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < minimum):
        raise SearchTreeError(f"{name} must be an integer >= {minimum} or None, got {value!r}")


def build_search_tree(
    problem: Problem[S],
    strategy: str = "bfs",
    max_depth: int | None = None,
    max_nodes: int | None = 1_000_000,
    time_limit: float | None = None,
    duplicate_detection: bool = True,
    stop_at_goal: bool = True,
    record_invalid: bool = True,
    on_goal: Callable[[S], None] | None = None,
) -> SearchTree[S]:
    """Grow the search tree of ``problem``; see the module docstring."""
    if strategy not in STRATEGIES:
        raise SearchTreeError(f"strategy must be one of {', '.join(STRATEGIES)}, got {strategy!r}")
    _positive_or_none("max_depth", max_depth, 0)
    _positive_or_none("max_nodes", max_nodes, 1)
    if time_limit is not None and (
        isinstance(time_limit, bool) or not isinstance(time_limit, (int, float)) or time_limit <= 0
    ):
        raise SearchTreeError("time_limit must be a positive number or None")

    start = time.perf_counter()
    stats = TreeStats()
    root_state = problem.initial_state()
    nodes: list[TreeNode[S]] = [TreeNode(0, root_state, None, None, 0)]
    stats.nodes_generated = 1
    best_depth: dict[S, int] = {root_state: 0}   # state -> smallest depth generated
    goal_ids: list[int] = []

    if problem.is_goal(root_state):
        nodes[0].status = GOAL
        goal_ids.append(0)
        stats.goals_found = 1
        if on_goal:
            on_goal(root_state)

    frontier: deque[int] = deque()
    if not goal_ids or not stop_at_goal:
        frontier.append(0)
    stats.max_frontier = len(frontier)

    def add_node(state, parent, action, depth, status, reason="") -> TreeNode[S]:
        node = TreeNode(len(nodes), state, parent.id, action, depth, status, reason)
        nodes.append(node)
        parent.children.append(node.id)
        stats.nodes_generated += 1
        stats.max_depth = max(stats.max_depth, depth)
        return node

    finished = False
    while frontier and not finished:
        if max_nodes is not None and stats.nodes_generated >= max_nodes:
            stats.limit_reached = "max_nodes"
            break
        if time_limit is not None and time.perf_counter() - start >= time_limit:
            stats.limit_reached = "time_limit"
            break
        node = nodes[frontier.popleft() if strategy == "bfs" else frontier.pop()]
        if node.status == GOAL:          # only when stop_at_goal is False
            continue
        if max_depth is not None and node.depth >= max_depth:
            node.status = DEPTH_LIMIT
            stats.depth_limit_leaves += 1
            continue

        node.status = EXPANDED
        stats.nodes_expanded += 1
        node.order = stats.nodes_expanded
        new_children: list[int] = []
        for move in problem.expand(node.state):
            stats.transitions_examined += 1
            depth = node.depth + 1
            if not move.valid:
                stats.invalid_transitions += 1
                if record_invalid:
                    add_node(move.state, node, move.action, depth, INVALID, move.reason)
                continue
            stats.valid_transitions += 1
            if duplicate_detection and move.state in best_depth and best_depth[move.state] <= depth:
                stats.duplicates += 1
                add_node(move.state, node, move.action, depth, DUPLICATE,
                         f"state already generated at depth {best_depth[move.state]}")
                continue
            best_depth[move.state] = depth
            child = add_node(move.state, node, move.action, depth, FRONTIER)
            stats.max_new_state_depth = max(stats.max_new_state_depth, depth)
            if problem.is_goal(move.state):    # goal test on generation
                child.status = GOAL
                goal_ids.append(child.id)
                stats.goals_found += 1
                if on_goal:
                    on_goal(move.state)
                if stop_at_goal:
                    finished = True
                    break
                continue
            new_children.append(child.id)
        if not new_children and not finished and not any(
            nodes[c].status == GOAL for c in node.children
        ):
            node.status = DEAD_END
            stats.dead_ends += 1
        # DFS pushes children in reverse so the first action is explored first.
        frontier.extend(new_children if strategy == "bfs" else reversed(new_children))
        stats.max_frontier = max(stats.max_frontier, len(frontier))

    stats.unique_states = len(best_depth)
    stats.elapsed_seconds = time.perf_counter() - start
    return SearchTree(nodes, stats, strategy, goal_ids)
