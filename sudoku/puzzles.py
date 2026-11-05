"""Predefined puzzles and the measured difficulty classification.

Difficulty is NOT assigned by clue count. A puzzle is classified from the
statistics of an actual BFS run (MRV variable order, the default):

* Easy   - solved without any backtracking: every expanded state has exactly
           one legal digit for its MRV cell (max queue size 1).
* Medium - needs backtracking, but at most ``MEDIUM_MAX_STATES`` expanded states.
* Hard   - needs more than ``MEDIUM_MAX_STATES`` expanded states.

``tests/test_sudoku.py`` re-runs the solver and checks that every predefined
puzzle really falls into its declared level.
"""

from __future__ import annotations

from .model import Grid, SudokuError, parse_grid
from .solver import SearchStats

MEDIUM_MAX_STATES = 1_000

PUZZLES: dict[str, str] = {
    # Example puzzle from the Wikipedia "Sudoku" article (30 clues).
    "easy": "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79",
    # 27 clues.
    "medium": "..9748...7.........2.1.9.....7...24..64.1.59..98...3.....8.3.2.........6...2759..",
    # Arto Inkala's puzzle published in 2012 as "the world's hardest Sudoku" (21 clues).
    "hard": "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..",
}

# Extra puzzles used only to show that clue count does not determine difficulty.
EXTRA_PUZZLES: dict[str, str] = {
    "extra-17-clues": "4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......",
    "extra-36-clues": "...26.7.168..7..9.19...45..82.1...4...46.29...5...3.28..93...74.4..5..367.3.18...",
}

DIFFICULTIES = tuple(PUZZLES)


def get_puzzle(difficulty: str) -> Grid:
    key = difficulty.lower()
    if key not in PUZZLES:
        raise SudokuError(
            f"Unknown difficulty {difficulty!r}; choose one of {', '.join(DIFFICULTIES)}"
        )
    return parse_grid(PUZZLES[key])


def classify_difficulty(stats: SearchStats) -> str:
    """Map measured MRV-BFS statistics of a solved puzzle to a difficulty."""
    if stats.backtracks == 0 and stats.max_queue_size <= 1:
        return "easy"
    if stats.states_expanded <= MEDIUM_MAX_STATES:
        return "medium"
    return "hard"
