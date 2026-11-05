"""Theoretical (analytical) search-landscape figures for Latin squares."""

from __future__ import annotations

from dataclasses import dataclass
from math import factorial

from .model import Grid, check_grid

# Number of Latin squares L(n) and reduced Latin squares R(n) of order n
# (OEIS A002860 and A000315). Literature constants quoted for comparison;
# the tests reproduce n <= 4 (all squares) and n <= 6 (reduced) by exhaustive
# search. Relation: L(n) = n! * (n-1)! * R(n).
KNOWN_LATIN_SQUARES = {1: 1, 2: 2, 3: 12, 4: 576, 5: 161_280, 6: 812_851_200, 7: 61_479_419_904_000}
KNOWN_REDUCED_SQUARES = {1: 1, 2: 1, 3: 1, 4: 4, 5: 56, 6: 9_408, 7: 16_942_080}


@dataclass(frozen=True)
class TheoreticalLandscape:
    """Analytical size of the Latin square search space."""

    n: int
    cells: int                        # n^2
    free_cells: int                   # D = search depth
    naive_assignments: int            # n^D
    row_permutation_bound: int        # (n!)^n for the empty grid
    full_tree_nodes: int              # sum_{d=0..D} n^d (no pruning)
    iddfs_unpruned_nodes: int         # sum_{L=0..D} sum_{d=0..L} n^d
    known_latin_squares: int | None   # L(n)
    known_reduced_squares: int | None  # R(n)
    max_branching_factor: int         # n


def compute_theoretical_landscape(n: int, prefill: Grid) -> TheoreticalLandscape:
    check_grid(prefill, n)
    free = sum(1 for row in prefill for v in row if v == 0)
    level = [n ** d for d in range(free + 1)]
    cumulative, running = [], 0
    for size in level:
        running += size
        cumulative.append(running)
    return TheoreticalLandscape(
        n=n,
        cells=n * n,
        free_cells=free,
        naive_assignments=n ** free,
        row_permutation_bound=factorial(n) ** n,
        full_tree_nodes=cumulative[-1],
        iddfs_unpruned_nodes=sum(cumulative),
        known_latin_squares=KNOWN_LATIN_SQUARES.get(n),
        known_reduced_squares=KNOWN_REDUCED_SQUARES.get(n),
        max_branching_factor=n,
    )
