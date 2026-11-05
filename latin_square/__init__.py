"""Latin Square: CSP model, IDDFS with backtracking, validator."""

from .landscape import TheoreticalLandscape, compute_theoretical_landscape
from .model import Grid, LatinSquareError, empty_grid, format_grid, parse_grid, reduced_prefill
from .objective import ObjectiveValue, evaluate
from .solver import IterationStats, LatinSquareIDDFS, SearchLimits, SearchResult, SearchStats
from .validator import ValidationReport, validate_latin_square

__all__ = [
    "Grid", "IterationStats", "LatinSquareError", "LatinSquareIDDFS", "ObjectiveValue",
    "SearchLimits", "SearchResult", "SearchStats", "TheoreticalLandscape", "ValidationReport",
    "compute_theoretical_landscape", "empty_grid", "evaluate", "format_grid", "parse_grid",
    "reduced_prefill", "validate_latin_square",
]
