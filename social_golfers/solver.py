"""Depth First Search with Backtracking for the Social Golfers Problem.

Search state
    A partial schedule filled slot by slot in the fixed order
    week -> group -> slot. The depth of a state is the number of filled slots.

Transition (successor function)
    Put one golfer into the next empty slot:
    * slot 0 of a group: the smallest golfer not yet placed this week
      (forced; this is the canonical form of a set partition);
    * other slots: any golfer larger than the previous one in the group that
      is not yet placed this week (golfers ascend inside a group).

Pruning (a candidate is rejected before it becomes a node when)
    * it already met a member of the current group (constraint C4);
    * week-symmetry breaking is violated (see below);
    * forward check: not enough compatible golfers remain to fill the group.

Backtracking
    When every candidate of a state fails, the last assignment is undone
    (the slot, the week-usage bit and the pair bits are restored) and DFS
    continues with the next candidate of the parent state.

Symmetry breaking (optional, on by default, sound - loses no solution class)
    * golfer relabelling: week 1 is fixed to {0..p-1}, {p..2p-1}, ...;
    * week order: from week 2 on, the partner of golfer 0 (slot 1 of group 1)
      strictly increases from week to week.
"""

from __future__ import annotations

import copy
import sys
import time
from dataclasses import dataclass, field

from .model import ConfigurationError, GolferConfig, Schedule, require_int


@dataclass(frozen=True)
class SearchLimits:
    """Resource limits; ``None`` means unlimited."""

    max_nodes: int | None = 2_000_000
    time_limit: float | None = None

    def __post_init__(self) -> None:
        if self.max_nodes is not None:
            require_int("max_nodes", self.max_nodes, 1)
        if self.time_limit is not None:
            if isinstance(self.time_limit, bool) or not isinstance(
                self.time_limit, (int, float)
            ):
                raise ConfigurationError("time_limit must be a number")
            if self.time_limit <= 0:
                raise ConfigurationError("time_limit must be > 0")


@dataclass
class SearchStats:
    """Measured (experimental) statistics of one DFS run."""

    states_expanded: int = 0         # states whose successors were generated
    candidates_generated: int = 0    # successor candidates produced
    assignments: int = 0             # candidates accepted -> new search nodes
    rejected_pair_conflict: int = 0  # violated C4
    rejected_symmetry: int = 0       # violated week-order symmetry breaking
    rejected_forward_check: int = 0  # group could no longer be completed
    rejected_week_check: int = 0     # a closed group left the week uncompletable
    dead_ends: int = 0               # states with no accepted successor
    backtracks: int = 0              # assignments undone
    fixed_assignments: int = 0       # slots fixed by symmetry breaking (week 1)
    max_depth_reached: int = 0       # deepest number of filled slots
    fitness_evaluations: int = 0     # f(S) evaluated at each completed week
    solutions_found: int = 0
    nodes_per_week: list[int] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    limit_reached: str | None = None

    @property
    def candidate_validity_ratio(self) -> float:
        """Share of generated candidates that passed every check."""
        return self.assignments / self.candidates_generated if self.candidates_generated else 0.0

    @property
    def raw_branching_factor(self) -> float:
        """Average number of candidates generated per expanded state."""
        return self.candidates_generated / self.states_expanded if self.states_expanded else 0.0

    @property
    def effective_branching_factor(self) -> float:
        """Average number of accepted successors per expanded state."""
        return self.assignments / self.states_expanded if self.states_expanded else 0.0


@dataclass
class SearchResult:
    """Best schedule found plus the statistics of the run."""

    config: GolferConfig
    target_weeks: int
    best_weeks: int
    schedule: Schedule
    stats: SearchStats
    search_completed: bool   # True if no limit interrupted the search
    symmetry_breaking: bool
    count_all: bool

    @property
    def target_reached(self) -> bool:
        return self.best_weeks >= self.target_weeks

    @property
    def proven_maximum(self) -> bool:
        """True when ``best_weeks`` is provably the maximum number of weeks.

        Either it meets the theoretical upper bound, or the search finished
        without hitting a limit and could not reach the target (so the whole
        pruned space was explored).
        """
        if self.best_weeks == self.config.week_upper_bound:
            return True
        return self.search_completed and not self.target_reached


class _LimitReached(Exception):
    """Internal signal used to unwind the recursion when a limit is hit."""


class SocialGolfersDFS:
    """DFS with backtracking that looks for a ``target_weeks`` schedule.

    It keeps the deepest feasible schedule seen, so if the target is out of
    reach (or a limit is hit) the result is the maximum number of weeks
    found. With ``count_all=True`` it does not stop at the first solution and
    counts every target-length schedule in the (pruned) search space.
    """

    _TIME_CHECK_INTERVAL = 1024

    def __init__(
        self,
        config: GolferConfig,
        target_weeks: int | None = None,
        limits: SearchLimits | None = None,
        symmetry_breaking: bool = True,
        count_all: bool = False,
    ) -> None:
        self.config = config
        self.target = (
            config.week_upper_bound
            if target_weeks is None
            else require_int("target weeks (w)", target_weeks, 1)
        )
        self.limits = limits if limits is not None else SearchLimits()
        self.symmetry_breaking = symmetry_breaking
        self.count_all = count_all

    # ------------------------------------------------------------------ API
    def solve(self) -> SearchResult:
        n, g = self.config.num_golfers, self.config.groups
        self.stats = SearchStats(nodes_per_week=[0] * self.target)
        self._full = (1 << n) - 1
        self._met = [0] * n                       # met[i]: bitmask of partners of i
        self._week_used = [0] * self.target       # golfers placed in each week
        self._schedule: Schedule = [[[] for _ in range(g)] for _ in range(self.target)]
        self._best_weeks = 0
        self._best: Schedule = []
        self._start = time.perf_counter()

        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old_limit, n * self.target + 500))
        try:
            if self.symmetry_breaking:
                self._fix_first_week()
                if not self._on_week_complete(0) and self.target > 1:
                    self._extend(1, 0, 0)
            else:
                self._extend(0, 0, 0)
        except _LimitReached:
            pass
        finally:
            sys.setrecursionlimit(old_limit)
            self.stats.elapsed_seconds = time.perf_counter() - self._start

        return SearchResult(
            config=self.config,
            target_weeks=self.target,
            best_weeks=self._best_weeks,
            schedule=self._best,
            stats=self.stats,
            search_completed=self.stats.limit_reached is None,
            symmetry_breaking=self.symmetry_breaking,
            count_all=self.count_all,
        )

    # ------------------------------------------------------------ internals
    def _fix_first_week(self) -> None:
        """Week 1 = {0..p-1}, {p..2p-1}, ... (golfer-relabelling symmetry)."""
        p = self.config.group_size
        for k in range(self.config.groups):
            for golfer in range(k * p, (k + 1) * p):
                self._place(0, k, golfer)
        self.stats.fixed_assignments = self.config.num_golfers
        self.stats.max_depth_reached = self.config.num_golfers

    def _check_limits(self) -> None:
        stats, limits = self.stats, self.limits
        if limits.max_nodes is not None and stats.states_expanded >= limits.max_nodes:
            stats.limit_reached = "max_nodes"
            raise _LimitReached
        if (
            limits.time_limit is not None
            and stats.states_expanded % self._TIME_CHECK_INTERVAL == 0
            and time.perf_counter() - self._start >= limits.time_limit
        ):
            stats.limit_reached = "time_limit"
            raise _LimitReached

    def _candidates(self, week: int, group: list[int]) -> list[int]:
        """Successor golfers for the next slot of ``group`` (in ascending order)."""
        free = self._full & ~self._week_used[week]
        if not group:
            # Forced choice: the smallest golfer not yet placed this week.
            return [(free & -free).bit_length() - 1]
        above = free & ~((1 << (group[-1] + 1)) - 1)
        result = []
        while above:
            low = above & -above
            result.append(low.bit_length() - 1)
            above ^= low
        return result

    def _group_can_be_completed(self, week: int, group: list[int], golfer: int) -> bool:
        """Forward check: enough compatible golfers remain to fill the group."""
        remaining = self.config.group_size - len(group) - 1
        if remaining == 0:
            return True
        pool = self._full & ~self._week_used[week] & ~((1 << (golfer + 1)) - 1)
        pool &= ~self._met[golfer]
        for member in group:
            pool &= ~self._met[member]
        return pool.bit_count() >= remaining

    def _week_can_be_completed(self, week: int) -> bool:
        """Forward check after a group is closed: every golfer still unplaced
        this week must have at least ``p - 1`` compatible unplaced golfers,
        otherwise no group can be formed for it (necessary condition)."""
        need = self.config.group_size - 1
        pool = self._full & ~self._week_used[week]
        rest = pool
        while rest:
            low = rest & -rest
            golfer = low.bit_length() - 1
            if (pool & ~low & ~self._met[golfer]).bit_count() < need:
                return False
            rest ^= low
        return True

    def _place(self, week: int, k: int, golfer: int) -> None:
        group = self._schedule[week][k]
        bit = 1 << golfer
        for member in group:
            self._met[member] |= bit
            self._met[golfer] |= 1 << member
        group.append(golfer)
        self._week_used[week] |= bit

    def _undo(self, week: int, k: int) -> None:
        group = self._schedule[week][k]
        golfer = group.pop()
        bit = 1 << golfer
        self._week_used[week] &= ~bit
        for member in group:
            self._met[member] &= ~bit
            self._met[golfer] &= ~(1 << member)

    def _on_week_complete(self, week: int) -> bool:
        """Evaluate f(S) = completed weeks; return True if the search must stop."""
        self.stats.fitness_evaluations += 1
        weeks_done = week + 1
        if weeks_done > self._best_weeks:
            self._best_weeks = weeks_done
            self._best = copy.deepcopy(self._schedule[:weeks_done])
        if weeks_done == self.target:
            self.stats.solutions_found += 1
            return not self.count_all
        return False

    def _extend(self, week: int, k: int, slot: int) -> bool:
        """Expand the state whose next empty slot is (week, k, slot).

        Returns True when the search must stop (first solution found).
        """
        self._check_limits()
        stats = self.stats
        stats.states_expanded += 1
        n, g, p = self.config.num_golfers, self.config.groups, self.config.group_size
        depth = week * n + k * p + slot
        if depth > stats.max_depth_reached:
            stats.max_depth_reached = depth

        group = self._schedule[week][k]
        group_mask = 0
        for member in group:
            group_mask |= 1 << member
        order_weeks = self.symmetry_breaking and week >= 2 and k == 0 and slot == 1
        accepted_any = False

        for golfer in self._candidates(week, group):
            stats.candidates_generated += 1
            if self._met[golfer] & group_mask:
                stats.rejected_pair_conflict += 1
                continue
            if order_weeks and golfer <= self._schedule[week - 1][0][1]:
                stats.rejected_symmetry += 1
                continue
            if not self._group_can_be_completed(week, group, golfer):
                stats.rejected_forward_check += 1
                continue

            self._place(week, k, golfer)
            if slot == p - 1 and k < g - 1 and not self._week_can_be_completed(week):
                self._undo(week, k)
                stats.rejected_week_check += 1
                continue
            stats.assignments += 1
            stats.nodes_per_week[week] += 1
            accepted_any = True

            if slot < p - 1:
                stop = self._extend(week, k, slot + 1)
            elif k < g - 1:
                stop = self._extend(week, k + 1, 0)
            else:
                if depth + 1 > stats.max_depth_reached:
                    stats.max_depth_reached = depth + 1
                stop = self._on_week_complete(week)
                if not stop and week + 1 < self.target:
                    stop = self._extend(week + 1, 0, 0)
            if stop:
                return True

            self._undo(week, k)
            stats.backtracks += 1

        if not accepted_any:
            stats.dead_ends += 1
        return False
