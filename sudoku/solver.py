"""Breadth First Search with Backtracking for Sudoku.

Search state
    A consistent partial grid (no unit contains a repeated digit) together
    with the digits already used in every row, column and box. The depth of a
    state is the number of cells filled by the search (the root has depth 0).

Transition
    Choose ONE empty cell of the state (deterministically: the cell with the
    fewest legal digits - "MRV" - or the first empty cell in row-major order)
    and create one child for each digit 1..9 written into that cell. Every
    expansion fills exactly one cell, so BFS level ``d`` holds exactly the
    states with ``d`` filled cells.

Breadth First Search
    States are stored in a FIFO queue (``collections.deque``): children are
    appended at the back with ``append`` and states are expanded from the
    front with ``popleft``. All states of depth ``d`` are therefore expanded
    before any state of depth ``d + 1``.

Backtracking (how it works inside BFS)
    BFS keeps every alternative of the current level in its queue instead of
    on a recursion stack. A partial assignment is checked incrementally the
    moment it is generated:
    * a digit that already appears in the cell's row, column or box is
      rejected (invalid partial state);
    * forward check: if writing the digit leaves some empty peer cell with no
      legal digit, the child is a dead end and is discarded.
    Discarding a dead end abandons that partial assignment and the search
    resumes with the next alternative waiting in the queue - this is the
    backtracking step. A whole branch is abandoned when an expanded state has
    no surviving child. Each state also keeps a parent link, so the solution
    path is recovered by tracing back from the goal to the root.

Duplicate detection
    A set of visited grids prevents enqueuing the same partial grid twice.
    Because the variable choice is a deterministic function of the state,
    every partial grid has a unique path from the root, so the set is a
    safety net and the measured number of duplicates is 0.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from .model import (
    ALL_DIGITS_MASK,
    CELLS,
    DIGITS,
    Grid,
    SudokuError,
    box_of,
    check_puzzle,
    col_of,
    row_of,
)

VARIABLE_ORDERS = ("mrv", "row-major")


def _build_peers() -> tuple[tuple[int, ...], ...]:
    peers = []
    for cell in range(CELLS):
        peers.append(tuple(
            other for other in range(CELLS)
            if other != cell and (
                row_of(other) == row_of(cell)
                or col_of(other) == col_of(cell)
                or box_of(other) == box_of(cell)
            )
        ))
    return tuple(peers)


PEERS = _build_peers()  # 20 peers per cell
ROW = tuple(row_of(c) for c in range(CELLS))
COL = tuple(col_of(c) for c in range(CELLS))
BOXES = tuple(box_of(c) for c in range(CELLS))


@dataclass(slots=True)
class SearchNode:
    """One BFS state: a consistent partial grid plus used-digit bitmasks."""

    grid: Grid
    rows: tuple[int, ...]
    cols: tuple[int, ...]
    boxes: tuple[int, ...]
    empty: int
    depth: int
    parent: "SearchNode | None" = None
    cell: int | None = None    # the assignment that created this node
    digit: int | None = None

    def candidates(self, cell: int) -> int:
        """Bitmask of digits that can legally be written into ``cell``."""
        used = self.rows[ROW[cell]] | self.cols[COL[cell]] | self.boxes[BOXES[cell]]
        return ALL_DIGITS_MASK & ~used


@dataclass(frozen=True)
class SearchLimits:
    """Resource limits; None means unlimited."""

    max_states: int | None = 1_000_000    # expanded states
    max_queue: int | None = 2_000_000     # simultaneous states in the queue
    time_limit: float | None = None       # seconds

    def __post_init__(self) -> None:
        for name in ("max_states", "max_queue"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 1
            ):
                raise SudokuError(f"{name} must be a positive integer or None")
        if self.time_limit is not None and (
            isinstance(self.time_limit, bool)
            or not isinstance(self.time_limit, (int, float))
            or self.time_limit <= 0
        ):
            raise SudokuError("time_limit must be a positive number or None")


@dataclass
class SearchStats:
    """Measured statistics of one BFS run."""

    initial_empty: int = 0
    states_expanded: int = 0          # states removed from the queue and expanded
    states_generated: int = 0         # consistent, non-dead children kept
    candidates_tested: int = 0        # (state, digit) pairs tried
    rejected_conflicts: int = 0       # invalid partial states (digit repeated in a unit)
    pruned_dead_ends: int = 0         # consistent children killed by the forward check
    failed_expansions: int = 0        # expanded states with no surviving child
    duplicates_skipped: int = 0
    max_queue_size: int = 0
    max_depth: int = 0
    solutions_found: int = 0
    frontier_per_depth: list[int] = field(default_factory=list)  # states generated per depth
    elapsed_seconds: float = 0.0
    limit_reached: str | None = None

    @property
    def backtracks(self) -> int:
        """Abandoned consistent partial assignments (dead ends).

        Every enqueued state has at least one legal digit in every empty cell
        (the root is checked, children are forward-checked), so a failed
        expansion can only be caused by pruned children; counting both would
        count the same dead end twice.
        """
        return self.pruned_dead_ends

    @property
    def raw_branching_factor(self) -> float:
        """Digits tried per expanded state (always 9 in this formulation)."""
        return self.candidates_tested / self.states_expanded if self.states_expanded else 0.0

    @property
    def consistent_branching_factor(self) -> float:
        """Digits that do not conflict with the state, per expanded state."""
        if not self.states_expanded:
            return 0.0
        return (self.candidates_tested - self.rejected_conflicts) / self.states_expanded

    @property
    def effective_branching_factor(self) -> float:
        """Children actually kept per expanded state."""
        return self.states_generated / self.states_expanded if self.states_expanded else 0.0


@dataclass
class SearchResult:
    """Outcome of one BFS run: status, solutions, path, statistics."""

    status: str                       # "solved", "no_solution" or "limit_reached"
    puzzle: Grid
    solutions: list[Grid]
    path: list[tuple[int, int]]       # (cell, digit) assignments of the first solution
    stats: SearchStats
    variable_order: str

    @property
    def solution(self) -> Grid | None:
        return self.solutions[0] if self.solutions else None

    @property
    def search_completed(self) -> bool:
        return self.stats.limit_reached is None


class _LimitReached(Exception):
    pass


class SudokuBFS:
    """Breadth First Search with backtracking over partial Sudoku grids."""

    def __init__(
        self,
        puzzle: Grid,
        limits: SearchLimits | None = None,
        variable_order: str = "mrv",
        count_all: bool = False,
    ) -> None:
        self.puzzle = check_puzzle(puzzle)
        if variable_order not in VARIABLE_ORDERS:
            raise SudokuError(
                f"variable_order must be one of {', '.join(VARIABLE_ORDERS)}, got {variable_order!r}"
            )
        self.limits = limits if limits is not None else SearchLimits()
        self.variable_order = variable_order
        self.count_all = count_all

    # ------------------------------------------------------------------ API
    def solve(self) -> SearchResult:
        stats = SearchStats()
        self.stats = stats
        solutions: list[Grid] = []
        first_goal: SearchNode | None = None
        start = time.perf_counter()

        root = self._make_root()
        stats.initial_empty = root.empty
        stats.frontier_per_depth = [0] * (root.empty + 1)
        stats.frontier_per_depth[0] = 1

        try:
            if not self._root_is_consistent(root):
                stats.failed_expansions += 1
            elif root.empty == 0:
                solutions.append(root.grid)
                first_goal = root
                stats.solutions_found = 1
            else:
                queue: deque[SearchNode] = deque([root])   # FIFO frontier
                visited: set[Grid] = {root.grid}
                stats.max_queue_size = 1
                while queue:
                    self._check_limits(start, len(queue))
                    node = queue.popleft()                 # expand the OLDEST state
                    stats.states_expanded += 1
                    kept = 0
                    for child in self._expand(node):
                        if child.grid in visited:
                            stats.duplicates_skipped += 1
                            continue
                        visited.add(child.grid)
                        kept += 1
                        stats.states_generated += 1
                        stats.frontier_per_depth[child.depth] += 1
                        stats.max_depth = max(stats.max_depth, child.depth)
                        if child.empty == 0:               # goal test on generation
                            stats.solutions_found += 1
                            solutions.append(child.grid)
                            if first_goal is None:
                                first_goal = child
                            if not self.count_all:
                                raise _Solved
                        else:
                            queue.append(child)            # enqueue at the BACK
                    stats.max_queue_size = max(stats.max_queue_size, len(queue))
                    if kept == 0:
                        stats.failed_expansions += 1       # whole branch abandoned
        except _Solved:
            pass
        except _LimitReached:
            pass
        stats.elapsed_seconds = time.perf_counter() - start

        if solutions:
            status = "solved"
        elif stats.limit_reached:
            status = "limit_reached"
        else:
            status = "no_solution"
        return SearchResult(
            status=status,
            puzzle=self.puzzle,
            solutions=solutions,
            path=self._trace_path(first_goal),
            stats=stats,
            variable_order=self.variable_order,
        )

    # ------------------------------------------------------------ internals
    def _make_root(self) -> SearchNode:
        rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
        for cell, digit in enumerate(self.puzzle):
            if digit:
                bit = 1 << digit
                rows[ROW[cell]] |= bit
                cols[COL[cell]] |= bit
                boxes[BOXES[cell]] |= bit
        empty = sum(1 for d in self.puzzle if d == 0)
        return SearchNode(self.puzzle, tuple(rows), tuple(cols), tuple(boxes), empty, 0)

    @staticmethod
    def _root_is_consistent(root: SearchNode) -> bool:
        """Forward check on the initial puzzle: every empty cell needs a digit."""
        return all(root.candidates(c) for c in range(CELLS) if root.grid[c] == 0)

    def _check_limits(self, start: float, queue_size: int) -> None:
        stats, limits = self.stats, self.limits
        if limits.max_states is not None and stats.states_expanded >= limits.max_states:
            stats.limit_reached = "max_states"
        elif limits.max_queue is not None and queue_size > limits.max_queue:
            stats.limit_reached = "max_queue"
        elif (
            limits.time_limit is not None
            and stats.states_expanded % 256 == 0
            and time.perf_counter() - start >= limits.time_limit
        ):
            stats.limit_reached = "time_limit"
        if stats.limit_reached:
            raise _LimitReached

    def _select_cell(self, node: SearchNode) -> int:
        grid = node.grid
        if self.variable_order == "row-major":
            return grid.index(0)
        best_cell, best_count = -1, 10
        for cell in range(CELLS):
            if grid[cell] == 0:
                count = node.candidates(cell).bit_count()
                if count < best_count:
                    best_cell, best_count = cell, count
                    if count <= 1:
                        break
        return best_cell

    def _expand(self, node: SearchNode):
        """Yield the consistent, non-dead-end children of ``node``."""
        stats = self.stats
        cell = self._select_cell(node)
        r, c, b = ROW[cell], COL[cell], BOXES[cell]
        legal = node.candidates(cell)
        for digit in DIGITS:
            stats.candidates_tested += 1
            bit = 1 << digit
            if not legal & bit:
                stats.rejected_conflicts += 1          # would repeat a digit in a unit
                continue
            grid = list(node.grid)
            grid[cell] = digit
            rows, cols, boxes = list(node.rows), list(node.cols), list(node.boxes)
            rows[r] |= bit
            cols[c] |= bit
            boxes[b] |= bit
            child = SearchNode(
                tuple(grid), tuple(rows), tuple(cols), tuple(boxes),
                node.empty - 1, node.depth + 1, node, cell, digit,
            )
            if any(grid[p] == 0 and not child.candidates(p) for p in PEERS[cell]):
                stats.pruned_dead_ends += 1            # dead end: backtrack
                continue
            yield child

    @staticmethod
    def _trace_path(goal: SearchNode | None) -> list[tuple[int, int]]:
        path = []
        node = goal
        while node is not None and node.cell is not None:
            path.append((node.cell, node.digit))
            node = node.parent
        path.reverse()
        return path


class _Solved(Exception):
    pass
