"""Iterative Deepening Depth First Search (IDDFS) with Backtracking.

Search state
    A consistent partial grid. The free (initially empty) cells are filled in
    a fixed row-major order, so the state at depth ``d`` has the first ``d``
    free cells assigned. Depth ``D`` (= number of free cells) is a complete
    grid.

Transition
    Write a value ``v`` in 1..n (ascending) into the next free cell.

Iterative deepening
    For depth limits ``L = 0, step, 2*step, ...`` (the last limit is always
    ``D``) run a depth-limited DFS (DLS) from the root. DLS does not expand
    nodes at depth ``L``; it reports *cutoff* if it stopped at the limit
    anywhere, *failure* if the subtree below the limit is exhausted without a
    cutoff, and *found* when it reaches a goal. Each iteration starts again
    from the root - the repeated work is the defining cost of IDDFS.

Backtracking
    A value that already appears in the cell's row or column is rejected
    before a node is created (early rejection). After a child subtree fails,
    the assignment is undone (grid cell and row/column bitmasks restored) and
    the next value is tried.

Avoiding unnecessary repeated computation (without changing IDDFS)
    * O(1) constraint checks with row/column bitmasks;
    * if an iteration finishes with no cutoff, deeper limits cannot find
      anything either, so the search stops and reports "no solution";
    * an optional ``step`` > 1 skips intermediate limits (the last limit is
      always the full depth);
    * symmetry breaking (reduced form, on by default): the first row and
      first column are fixed, which shrinks every iteration's tree.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

from .model import Grid, LatinSquareError, check_grid, empty_grid, reduced_prefill, require_size

FOUND, CUTOFF, FAILURE = "found", "cutoff", "failure"


@dataclass(frozen=True)
class SearchLimits:
    max_nodes: int | None = 5_000_000   # nodes visited, summed over all iterations
    time_limit: float | None = None     # seconds

    def __post_init__(self) -> None:
        if self.max_nodes is not None and (
            isinstance(self.max_nodes, bool) or not isinstance(self.max_nodes, int) or self.max_nodes < 1
        ):
            raise LatinSquareError("max_nodes must be a positive integer or None")
        if self.time_limit is not None and (
            isinstance(self.time_limit, bool)
            or not isinstance(self.time_limit, (int, float))
            or self.time_limit <= 0
        ):
            raise LatinSquareError("time_limit must be a positive number or None")


@dataclass
class IterationStats:
    """Measured statistics of one depth-limited DFS."""

    depth_limit: int
    nodes_visited: int = 0        # DLS calls (states reached)
    nodes_expanded: int = 0       # states whose children were generated
    values_tried: int = 0         # candidate (cell, value) pairs
    rejected_conflicts: int = 0   # invalid assignments (value repeated in row/column)
    assignments: int = 0          # valid assignments (children created)
    backtracks: int = 0           # assignments undone
    dead_ends: int = 0            # expanded states with no valid value
    cutoffs: int = 0              # states not expanded because depth == limit
    max_depth: int = 0
    outcome: str = ""             # found / cutoff / failure / limit
    elapsed_seconds: float = 0.0


@dataclass
class SearchStats:
    free_cells: int = 0
    iterations: list[IterationStats] = field(default_factory=list)
    solutions_found: int = 0
    elapsed_seconds: float = 0.0
    limit_reached: str | None = None

    def _total(self, name: str) -> int:
        return sum(getattr(it, name) for it in self.iterations)

    @property
    def nodes_visited(self) -> int:
        return self._total("nodes_visited")

    @property
    def nodes_expanded(self) -> int:
        return self._total("nodes_expanded")

    @property
    def values_tried(self) -> int:
        return self._total("values_tried")

    @property
    def rejected_conflicts(self) -> int:
        return self._total("rejected_conflicts")

    @property
    def assignments(self) -> int:
        return self._total("assignments")

    @property
    def backtracks(self) -> int:
        return self._total("backtracks")

    @property
    def dead_ends(self) -> int:
        return self._total("dead_ends")

    @property
    def final_iteration_nodes(self) -> int:
        return self.iterations[-1].nodes_visited if self.iterations else 0

    @property
    def repeated_work_ratio(self) -> float:
        """Total nodes over all iterations / nodes of the last iteration."""
        last = self.final_iteration_nodes
        return self.nodes_visited / last if last else 0.0

    @property
    def effective_branching_factor(self) -> float:
        expanded = self.nodes_expanded
        return self.assignments / expanded if expanded else 0.0


@dataclass
class SearchResult:
    status: str                 # "solved", "no_solution" or "limit_reached"
    n: int
    prefill: Grid
    solution: Grid | None
    stats: SearchStats

    @property
    def search_completed(self) -> bool:
        return self.stats.limit_reached is None


class _LimitReached(Exception):
    pass


class LatinSquareIDDFS:
    """Generate (or complete) an n x n Latin square with IDDFS + backtracking."""

    def __init__(
        self,
        n: int,
        prefill: Grid | None = None,
        limits: SearchLimits | None = None,
        step: int = 1,
        count_all: bool = False,
        reduced: bool = True,
    ) -> None:
        """``reduced=True`` (symmetry breaking) fixes the first row and the first
        column to 1..n. This is sound for generation: permuting the values makes
        the first row 1..n, then permuting rows 2..n makes the first column
        1..n, so every Latin square has an equivalent reduced one. It cannot be
        combined with a custom ``prefill``.
        """
        self.n = require_size(n)
        if prefill is not None and reduced:
            raise LatinSquareError("A custom pre-filled grid cannot be combined with reduced form")
        if prefill is not None:
            self.prefill = check_grid(prefill, n)
        else:
            self.prefill = reduced_prefill(n) if reduced else empty_grid(n)
        self.reduced = reduced
        if isinstance(step, bool) or not isinstance(step, int) or step < 1:
            raise LatinSquareError(f"step must be a positive integer, got {step!r}")
        self.step = step
        self.limits = limits if limits is not None else SearchLimits()
        self.count_all = count_all

    def depth_limits(self) -> list[int]:
        """The sequence of depth limits: 0, step, 2*step, ..., always ending at D."""
        free = sum(1 for row in self.prefill for v in row if v == 0)
        limits = list(range(0, free, self.step))
        limits.append(free)
        return limits

    # ------------------------------------------------------------------ API
    def solve(self) -> SearchResult:
        n = self.n
        self.grid = [list(row) for row in self.prefill]
        self.rows = [0] * n                    # bit v set: value v used in row
        self.cols = [0] * n
        for r in range(n):
            for c in range(n):
                v = self.grid[r][c]
                if v:
                    self.rows[r] |= 1 << v
                    self.cols[c] |= 1 << v
        self.free = [(r, c) for r in range(n) for c in range(n) if self.grid[r][c] == 0]
        self.stats = SearchStats(free_cells=len(self.free))
        self.solution: Grid | None = None
        self._start = time.perf_counter()

        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old_limit, len(self.free) + 500))
        try:
            for limit in self.depth_limits():
                it = IterationStats(depth_limit=limit)
                self.stats.iterations.append(it)
                self._it = it
                started = time.perf_counter()
                try:
                    outcome = self._dls(0, limit)
                except _LimitReached:
                    it.outcome = "limit"
                    raise
                finally:
                    it.elapsed_seconds = time.perf_counter() - started
                it.outcome = outcome
                if outcome == FOUND or self.stats.solutions_found:
                    break
                if outcome == FAILURE:   # no cutoff anywhere: nothing deeper exists
                    break
        except _LimitReached:
            pass
        finally:
            sys.setrecursionlimit(old_limit)
            self.stats.elapsed_seconds = time.perf_counter() - self._start

        if self.solution is not None:
            status = "solved"
        elif self.stats.limit_reached:
            status = "limit_reached"
        else:
            status = "no_solution"
        return SearchResult(status, n, self.prefill, self.solution, self.stats)

    # ------------------------------------------------------------ internals
    def _check_limits(self) -> None:
        stats, limits = self.stats, self.limits
        visited = stats.nodes_visited
        if limits.max_nodes is not None and visited >= limits.max_nodes:
            stats.limit_reached = "max_nodes"
        elif (
            limits.time_limit is not None
            and visited % 1024 == 0
            and time.perf_counter() - self._start >= limits.time_limit
        ):
            stats.limit_reached = "time_limit"
        if stats.limit_reached:
            raise _LimitReached

    def _dls(self, depth: int, limit: int) -> str:
        """Depth-limited DFS from the state with ``depth`` free cells assigned."""
        self._check_limits()
        it = self._it
        it.nodes_visited += 1
        if depth > it.max_depth:
            it.max_depth = depth

        if depth == len(self.free):            # goal test: complete, consistent grid
            self.stats.solutions_found += 1
            if self.solution is None:
                self.solution = tuple(tuple(row) for row in self.grid)
            return FAILURE if self.count_all else FOUND
        if depth == limit:                     # depth limit reached: do not expand
            it.cutoffs += 1
            return CUTOFF

        it.nodes_expanded += 1
        r, c = self.free[depth]
        used = self.rows[r] | self.cols[c]
        cutoff_occurred = False
        any_valid = False
        for v in range(1, self.n + 1):
            it.values_tried += 1
            bit = 1 << v
            if used & bit:                     # early rejection: row/column conflict
                it.rejected_conflicts += 1
                continue
            any_valid = True
            self.grid[r][c] = v                # assign
            self.rows[r] |= bit
            self.cols[c] |= bit
            it.assignments += 1
            outcome = self._dls(depth + 1, limit)
            if outcome == FOUND:
                return FOUND
            self.grid[r][c] = 0                # backtrack: undo the assignment
            self.rows[r] &= ~bit
            self.cols[c] &= ~bit
            it.backtracks += 1
            if outcome == CUTOFF:
                cutoff_occurred = True
        if not any_valid:
            it.dead_ends += 1
        return CUTOFF if cutoff_occurred else FAILURE
