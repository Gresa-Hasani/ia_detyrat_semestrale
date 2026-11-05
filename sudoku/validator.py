"""Independent Sudoku solution validator.

It does not use the solver's bitmasks or the ``UNITS`` table: rows, columns
and boxes are rebuilt here from plain index arithmetic and compared as sets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    """Errors found by the independent validator."""

    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_solution(solution: object, puzzle: object | None = None) -> ValidationReport:
    """Check that ``solution`` is a complete valid grid and keeps the clues."""
    report = ValidationReport()
    if not isinstance(solution, (list, tuple)) or len(solution) != 81:
        report.errors.append("Solution must contain exactly 81 cells")
        return report
    for i, value in enumerate(solution):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9:
            report.errors.append(f"Cell r{i // 9 + 1}c{i % 9 + 1} has invalid value {value!r}")
    if report.errors:
        return report

    expected = set(range(1, 10))
    for r in range(9):
        if set(solution[r * 9:(r + 1) * 9]) != expected:
            report.errors.append(f"Row {r + 1} does not contain digits 1-9 exactly once")
    for c in range(9):
        if {solution[r * 9 + c] for r in range(9)} != expected:
            report.errors.append(f"Column {c + 1} does not contain digits 1-9 exactly once")
    for br in range(3):
        for bc in range(3):
            box = {solution[(br * 3 + i) * 9 + bc * 3 + j] for i in range(3) for j in range(3)}
            if box != expected:
                report.errors.append(
                    f"Box {br * 3 + bc + 1} does not contain digits 1-9 exactly once"
                )

    if puzzle is not None:
        if not isinstance(puzzle, (list, tuple)) or len(puzzle) != 81:
            report.errors.append("Puzzle must contain exactly 81 cells")
            return report
        for i, given in enumerate(puzzle):
            if given and solution[i] != given:
                report.errors.append(
                    f"Clue at r{i // 9 + 1}c{i % 9 + 1} changed from {given} to {solution[i]}"
                )
    return report
