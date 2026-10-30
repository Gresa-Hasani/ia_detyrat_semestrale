"""Social Golfers Problem: CSP model, DFS with backtracking, validator."""

from .landscape import TheoreticalLandscape, compute_theoretical_landscape
from .model import ConfigurationError, GolferConfig, Schedule
from .objective import objective_value, repeated_pair_violations
from .solver import SearchLimits, SearchResult, SearchStats, SocialGolfersDFS
from .validator import ValidationReport, validate_schedule

__all__ = [
    "ConfigurationError",
    "GolferConfig",
    "Schedule",
    "SearchLimits",
    "SearchResult",
    "SearchStats",
    "SocialGolfersDFS",
    "TheoreticalLandscape",
    "ValidationReport",
    "compute_theoretical_landscape",
    "objective_value",
    "repeated_pair_violations",
    "validate_schedule",
]
