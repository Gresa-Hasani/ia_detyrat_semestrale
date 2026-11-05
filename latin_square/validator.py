"""Independent Latin Square validator (plain sets, no shared code with the solver)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_latin_square(square: object, n: int, prefill: object | None = None) -> ValidationReport:
    """Check that ``square`` is a complete n x n Latin square keeping ``prefill``."""
    report = ValidationReport()
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        report.errors.append(f"n must be a positive integer, got {n!r}")
        return report
    if not isinstance(square, (list, tuple)) or len(square) != n:
        report.errors.append(f"Square must have exactly {n} rows")
        return report
    for r, row in enumerate(square, start=1):
        if not isinstance(row, (list, tuple)) or len(row) != n:
            report.errors.append(f"Row {r} must have exactly {n} cells")
            return report
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= n:
                report.errors.append(f"Row {r} contains invalid value {value!r} (expected 1..{n})")
    if report.errors:
        return report

    expected = set(range(1, n + 1))
    for r in range(n):
        if set(square[r]) != expected:
            report.errors.append(f"Row {r + 1} does not contain 1..{n} exactly once")
    for c in range(n):
        if {square[r][c] for r in range(n)} != expected:
            report.errors.append(f"Column {c + 1} does not contain 1..{n} exactly once")

    if prefill is not None:
        for r in range(n):
            for c in range(n):
                given = prefill[r][c]
                if given and square[r][c] != given:
                    report.errors.append(
                        f"Pre-filled cell ({r + 1},{c + 1}) changed from {given} to {square[r][c]}"
                    )
    return report
