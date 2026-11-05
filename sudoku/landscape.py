"""Theoretical (analytical) search-landscape figures for a Sudoku puzzle.

These are computed from the puzzle alone, before any search. Measured figures
live in ``solver.SearchStats``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import prod

from .model import ALL_DIGITS_MASK, CELLS, Grid, box_of, check_puzzle, col_of, row_of

# Number of valid completed 9x9 Sudoku grids (Felgenhauer & Jarvis, 2005).
# A literature constant, quoted for comparison; not computed here.
VALID_COMPLETE_GRIDS = 6_670_903_752_021_072_936_960


@dataclass(frozen=True)
class TheoreticalLandscape:
    clues: int
    empty_cells: int                 # E = search depth
    naive_bound: int                 # 9^E
    domain_product_bound: int        # product of initial domain sizes
    total_candidates: int            # sum of initial domain sizes
    average_domain_size: float
    min_domain_size: int
    max_domain_size: int
    singleton_cells: int             # empty cells with exactly one legal digit


def initial_domains(grid: Grid) -> dict[int, int]:
    """Legal digit count of every empty cell, from the clues only."""
    domains = {}
    for cell in range(CELLS):
        if grid[cell]:
            continue
        used = 0
        for other in range(CELLS):
            if grid[other] and (
                row_of(other) == row_of(cell)
                or col_of(other) == col_of(cell)
                or box_of(other) == box_of(cell)
            ):
                used |= 1 << grid[other]
        domains[cell] = (ALL_DIGITS_MASK & ~used).bit_count()
    return domains


def compute_theoretical_landscape(grid: Grid) -> TheoreticalLandscape:
    check_puzzle(grid)
    sizes = list(initial_domains(grid).values())
    empty = len(sizes)
    return TheoreticalLandscape(
        clues=CELLS - empty,
        empty_cells=empty,
        naive_bound=9 ** empty,
        domain_product_bound=prod(sizes),
        total_candidates=sum(sizes),
        average_domain_size=sum(sizes) / empty if empty else 0.0,
        min_domain_size=min(sizes, default=0),
        max_domain_size=max(sizes, default=0),
        singleton_cells=sum(1 for s in sizes if s == 1),
    )
