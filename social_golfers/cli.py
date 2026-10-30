"""Command-line interface for the Social Golfers Problem."""

from __future__ import annotations

import argparse

from .landscape import compute_theoretical_landscape
from .model import ConfigurationError, GolferConfig
from .report import format_landscape, format_result, format_schedule
from .solver import SearchLimits, SocialGolfersDFS
from .validator import validate_schedule


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-g", "--groups", type=int, default=8, help="groups per week (default 8)")
    parser.add_argument("-p", "--size", type=int, default=4, help="golfers per group (default 4)")
    parser.add_argument(
        "-n", "--golfers", type=int, default=None,
        help="total golfers; optional, must equal g x p",
    )
    parser.add_argument(
        "-w", "--weeks", type=int, default=None,
        help="target weeks (default: theoretical upper bound)",
    )
    parser.add_argument(
        "--max-nodes", type=int, default=2_000_000,
        help="max expanded states, 0 = unlimited (default 2,000,000)",
    )
    parser.add_argument(
        "--time-limit", type=float, default=60.0,
        help="time limit in seconds, 0 = unlimited (default 60)",
    )
    parser.add_argument(
        "--no-symmetry-breaking", action="store_true",
        help="disable fixing week 1 and ordering the weeks",
    )
    parser.add_argument(
        "--count-solutions", action="store_true",
        help="do not stop at the first solution; count all target-length schedules",
    )


def run(args: argparse.Namespace) -> int:
    """Run the solver with parsed arguments; return a process exit code."""
    try:
        config = GolferConfig.from_parameters(args.groups, args.size, args.golfers)
        limits = SearchLimits(
            max_nodes=args.max_nodes or None,
            time_limit=args.time_limit or None,
        )
        solver = SocialGolfersDFS(
            config,
            target_weeks=args.weeks,
            limits=limits,
            symmetry_breaking=not args.no_symmetry_breaking,
            count_all=args.count_solutions,
        )
    except ConfigurationError as error:
        print(f"Error: {error}")
        return 2

    print(f"Social Golfers Problem: n={config.num_golfers}, g={config.groups}, "
          f"p={config.group_size}, target w={solver.target}")
    if solver.target > config.week_upper_bound:
        print(f"Warning: target exceeds the theoretical upper bound of "
              f"{config.week_upper_bound} weeks, so no full solution exists.")
    print("\nTheoretical landscape:")
    print(format_landscape(compute_theoretical_landscape(config, solver.target)))

    result = solver.solve()
    validation = validate_schedule(result.schedule, config, expected_weeks=result.best_weeks)
    print("\nMeasured search statistics (DFS with backtracking):")
    print(format_result(result, validation))
    print(f"\nBest schedule ({result.best_weeks} weeks):")
    print(format_schedule(result.schedule))
    return 0 if validation.is_valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="social_golfers",
        description="Social Golfers Problem solved with DFS and backtracking.",
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))
