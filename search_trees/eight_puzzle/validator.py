"""Independent 8-Puzzle solution validator.

It re-implements the move rule with explicit row/column arithmetic instead of
using the model's ``apply_move``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DELTAS = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    final_board: tuple[int, ...] | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _is_board(board: object) -> bool:
    return isinstance(board, (list, tuple)) and len(board) == 9 and sorted(board) == list(range(9))


def validate_solution(initial: object, goal: object, actions: list[str]) -> ValidationReport:
    """Replay ``actions`` from ``initial`` and check that every move is legal
    and that the final board equals ``goal``."""
    report = ValidationReport()
    if not _is_board(initial) or not _is_board(goal):
        report.errors.append("Initial and goal must be permutations of 0..8")
        return report
    board = list(initial)
    for step, action in enumerate(actions, start=1):
        if action not in DELTAS:
            report.errors.append(f"Step {step}: unknown action {action!r}")
            return report
        blank = board.index(0)
        r, c = blank // 3 + DELTAS[action][0], blank % 3 + DELTAS[action][1]
        if not (0 <= r < 3 and 0 <= c < 3):
            report.errors.append(f"Step {step}: move {action} leaves the board")
            return report
        board[blank], board[r * 3 + c] = board[r * 3 + c], board[blank]
    report.final_board = tuple(board)
    if tuple(board) != tuple(goal):
        report.errors.append(f"Final board {tuple(board)} differs from goal {tuple(goal)}")
    return report
