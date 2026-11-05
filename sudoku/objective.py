"""Objective function for Sudoku configurations.

For any grid ``x`` (complete or partial):

    V(x) = sum over the 27 units u, sum over digits d of max(0, n_{u,d}(x) - 1)
    E(x) = number of empty cells
    Phi(x) = V(x) + E(x)          (to be minimised)

``n_{u,d}(x)`` is how often digit ``d`` appears in unit ``u``. ``V`` counts
constraint violations (every extra copy of a digit in a unit is one
violation), ``E`` counts missing values. ``Phi(x) = 0`` exactly when ``x`` is
complete and violates no constraint, i.e. when ``x`` is a solution. A partial
state is *consistent* when ``V(x) = 0``; BFS only keeps consistent states, so
for them ``Phi(x) = E(x)``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .model import UNITS, Grid


@dataclass(frozen=True)
class ObjectiveValue:
    violations: int    # V(x)
    empty_cells: int   # E(x)

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
    violations = 0
    for _, cells in UNITS:
        counts = Counter(grid[c] for c in cells if grid[c])
        violations += sum(n - 1 for n in counts.values() if n > 1)
    return ObjectiveValue(violations, sum(1 for v in grid if v == 0))
