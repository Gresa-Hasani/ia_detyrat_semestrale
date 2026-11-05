"""Objective function for (partial) Latin squares.

    V(x)   = sum over rows and columns L, sum over values v of max(0, n_{L,v}(x) - 1)
    E(x)   = number of empty cells
    Phi(x) = V(x) + E(x)        (minimise)

``n_{L,v}(x)`` is how often value ``v`` appears in line ``L``. A partial grid
is consistent when ``V = 0``; ``Phi = 0`` exactly for a complete Latin square.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .model import Grid


@dataclass(frozen=True)
class ObjectiveValue:
    """V(x), E(x) and Phi(x) = V(x) + E(x) of a grid."""

    violations: int
    empty_cells: int

    @property
    def phi(self) -> int:
        return self.violations + self.empty_cells

    @property
    def is_consistent(self) -> bool:
        return self.violations == 0

    @property
    def is_solution(self) -> bool:
        return self.phi == 0


def evaluate(grid: Grid) -> ObjectiveValue:
    n = len(grid)
    lines = [list(row) for row in grid] + [[grid[r][c] for r in range(n)] for c in range(n)]
    violations = 0
    for line in lines:
        counts = Counter(v for v in line if v)
        violations += sum(k - 1 for k in counts.values() if k > 1)
    empty = sum(1 for row in grid for v in row if v == 0)
    return ObjectiveValue(violations, empty)
