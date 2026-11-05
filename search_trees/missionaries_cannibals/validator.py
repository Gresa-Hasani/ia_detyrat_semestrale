"""Independent state and solution validator for Missionaries and Cannibals."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_state(state: object, missionaries: int, cannibals: int) -> list[str]:
    """Errors of a single state ``(m_left, c_left, boat)``; empty list if valid."""
    if not isinstance(state, tuple) or len(state) != 3 or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in state
    ):
        return [f"State {state!r} must be a tuple of three integers"]
    m, c, b = state
    errors = []
    if not (0 <= m <= missionaries and 0 <= c <= cannibals):
        errors.append(f"State {state}: counts outside 0..{missionaries} / 0..{cannibals}")
        return errors
    if b not in (0, 1):
        errors.append(f"State {state}: boat side must be 0 or 1")
    for bank, (bm, bc) in (("left", (m, c)), ("right", (missionaries - m, cannibals - c))):
        if bm > 0 and bc > bm:
            errors.append(f"State {state}: missionaries outnumbered on the {bank} bank ({bc} > {bm})")
    return errors


def validate_solution(states: list, missionaries: int, cannibals: int, capacity: int) -> ValidationReport:
    """Check a whole path of states from (M, C, left) to (0, 0, right)."""
    report = ValidationReport()
    if not states:
        report.errors.append("Solution path is empty")
        return report
    if tuple(states[0]) != (missionaries, cannibals, 1):
        report.errors.append(f"Path must start at {(missionaries, cannibals, 1)}, got {states[0]}")
    if tuple(states[-1]) != (0, 0, 0):
        report.errors.append(f"Path must end at (0, 0, 0), got {states[-1]}")
    for state in states:
        report.errors.extend(validate_state(tuple(state), missionaries, cannibals))
    for i in range(1, len(states)):
        (m0, c0, b0), (m1, c1, b1) = states[i - 1], states[i]
        if b1 == b0:
            report.errors.append(f"Step {i}: the boat must change sides")
            continue
        moved_m, moved_c = (m0 - m1, c0 - c1) if b0 == 1 else (m1 - m0, c1 - c0)
        if moved_m < 0 or moved_c < 0:
            report.errors.append(f"Step {i}: people moved against the boat's direction")
        elif not 1 <= moved_m + moved_c <= capacity:
            report.errors.append(f"Step {i}: boat carries {moved_m + moved_c} people (capacity {capacity})")
    return report
