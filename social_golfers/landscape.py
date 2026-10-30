"""Theoretical (analytical) search-landscape figures for the SGP.

Everything here is computed from formulas, never from running the search.
Measured figures (expanded states, backtracks, ...) live in
``solver.SearchStats``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, factorial

from .model import GolferConfig, require_int


@dataclass(frozen=True)
class TheoreticalLandscape:
    """Analytical size of the search space for ``weeks`` weeks."""

    golfers: int
    groups: int
    group_size: int
    weeks: int
    week_upper_bound: int
    total_pairs: int                  # C(n, 2)
    pairs_used_per_week: int          # g * C(p, 2)
    possible_groups: int              # C(n, p)
    naive_assignments: int            # n^(n*w): every slot any golfer
    permutation_schedules: int        # (n!)^w: every week a permutation
    partitions_per_week: int          # n! / ((p!)^g * g!)
    partition_schedules: int          # P^w
    canonical_schedules_bound: int    # C(P - 1, w - 1)
    search_depth: int                 # n * w slots
    search_depth_with_fixed_week: int  # n * (w - 1)
    max_branching_factor: int         # n - 1 (second slot of group 1)


def compute_theoretical_landscape(config: GolferConfig, weeks: int) -> TheoreticalLandscape:
    """Compute the theoretical landscape of a ``weeks``-week schedule.

    * ``partitions_per_week``: ways to split ``n`` golfers into ``g``
      unordered groups of size ``p`` (multinomial divided by ``g!``).
    * ``canonical_schedules_bound``: with week 1 fixed (relabelling symmetry)
      and the other weeks forming a *set* of distinct partitions (week
      symmetry; two identical weeks would repeat pairs), at most
      ``C(P - 1, w - 1)`` candidate schedules remain before the pair
      constraint is applied.
    """
    require_int("weeks (w)", weeks, 1)
    n, g, p = config.num_golfers, config.groups, config.group_size
    partitions = factorial(n) // (factorial(p) ** g * factorial(g))
    return TheoreticalLandscape(
        golfers=n,
        groups=g,
        group_size=p,
        weeks=weeks,
        week_upper_bound=config.week_upper_bound,
        total_pairs=comb(n, 2),
        pairs_used_per_week=g * comb(p, 2),
        possible_groups=comb(n, p),
        naive_assignments=n ** (n * weeks),
        permutation_schedules=factorial(n) ** weeks,
        partitions_per_week=partitions,
        partition_schedules=partitions ** weeks,
        canonical_schedules_bound=comb(partitions - 1, weeks - 1),
        search_depth=n * weeks,
        search_depth_with_fixed_week=n * (weeks - 1),
        max_branching_factor=n - 1,
    )
