"""Sudoku: CSP model, Breadth First Search with backtracking, validator."""

from .landscape import TheoreticalLandscape, compute_theoretical_landscape
from .model import Grid, SudokuError, check_puzzle, find_conflicts, format_grid, parse_grid
from .objective import ObjectiveValue, evaluate
from .puzzles import PUZZLES, classify_difficulty, get_puzzle
from .solver import SearchLimits, SearchResult, SearchStats, SudokuBFS
from .validator import ValidationReport, validate_solution

__all__ = [
    "Grid", "ObjectiveValue", "PUZZLES", "SearchLimits", "SearchResult", "SearchStats",
    "SudokuBFS", "SudokuError", "TheoreticalLandscape", "ValidationReport", "check_puzzle",
    "classify_difficulty", "compute_theoretical_landscape", "evaluate", "find_conflicts",
    "format_grid", "get_puzzle", "parse_grid", "validate_solution",
]
