"""Command-line interface for the Latin Square generator."""

from __future__ import annotations

import argparse

from .landscape import compute_theoretical_landscape
from .model import LatinSquareError, format_grid, parse_grid
from .report import format_iterations, format_landscape, format_result
from .solver import LatinSquareIDDFS, SearchLimits
from .validator import validate_latin_square


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-n", "--size", type=int, default=5, help="order n of the square (default 5)")
    parser.add_argument(
        "--no-symmetry-breaking", action="store_true",
        help="do not fix the first row and column (search the full grid)",
    )
    parser.add_argument(
        "--prefill",
        help="extension: complete a partial grid, rows separated by '/', '.' = empty "
             "(e.g. \"1 . ./. . 1/. . .\"); implies --no-symmetry-breaking",
    )
    parser.add_argument("--step", type=int, default=1, help="depth-limit increment (default 1)")
    parser.add_argument("--count-solutions", action="store_true",
                        help="count all solutions in the last iteration instead of stopping at the first")
    parser.add_argument("--max-nodes", type=int, default=20_000_000,
                        help="max nodes over all iterations, 0 = unlimited (default 20,000,000)")
    parser.add_argument("--time-limit", type=float, default=120.0,
                        help="seconds, 0 = unlimited (default 120)")
    parser.add_argument("--hide-iterations", action="store_true",
                        help="do not print the per-iteration table")


def run(args: argparse.Namespace) -> int:
    try:
        prefill = parse_grid(args.prefill, args.size) if args.prefill else None
        limits = SearchLimits(max_nodes=args.max_nodes or None, time_limit=args.time_limit or None)
        solver = LatinSquareIDDFS(
            args.size, prefill, limits, args.step, args.count_solutions,
            reduced=prefill is None and not args.no_symmetry_breaking,
        )
    except LatinSquareError as error:
        print(f"Error: {error}")
        return 2

    mode = "custom pre-fill" if prefill else ("reduced form" if solver.reduced else "full grid")
    print(f"Latin Square n={solver.n} ({mode}) - IDDFS with backtracking, step {solver.step}\n")
    print("Initial state:")
    print(format_grid(solver.prefill))
    print("\nTheoretical landscape:")
    print(format_landscape(compute_theoretical_landscape(solver.n, solver.prefill)))

    result = solver.solve()
    validation = (
        validate_latin_square(result.solution, solver.n, solver.prefill) if result.solution else None
    )
    if not args.hide_iterations:
        print("\nNodes explored per depth limit:")
        print(format_iterations(result))
    print("\nMeasured search statistics:")
    print(format_result(result, validation))

    if result.solution is None:
        reason = "no Latin square completes this grid" if result.status == "no_solution" \
            else f"search limit reached ({result.stats.limit_reached})"
        print(f"\nNo solution: {reason}.")
        return 1
    print("\nLatin square:")
    print(format_grid(result.solution))
    return 0 if validation.is_valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="latin_square", description="Latin Square generated with IDDFS and backtracking."
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))
