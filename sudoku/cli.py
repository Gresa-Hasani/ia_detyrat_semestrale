"""Command-line interface for the Sudoku solver."""

from __future__ import annotations

import argparse
from pathlib import Path

from .landscape import compute_theoretical_landscape
from .model import SudokuError, format_grid, parse_grid
from .puzzles import DIFFICULTIES, classify_difficulty, get_puzzle
from .report import format_landscape, format_result
from .solver import VARIABLE_ORDERS, SearchLimits, SudokuBFS
from .validator import validate_solution


def add_arguments(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "-d", "--difficulty", choices=DIFFICULTIES, default="easy",
        help="predefined puzzle (default easy)",
    )
    source.add_argument("--puzzle", help="custom puzzle: 81 characters, '.' or '0' = empty")
    source.add_argument("--file", type=Path, help="read a custom puzzle from a text file")
    parser.add_argument(
        "--order", choices=VARIABLE_ORDERS, default="mrv",
        help="which empty cell each state expands (default mrv)",
    )
    parser.add_argument("--count-solutions", action="store_true",
                        help="keep searching after the first solution and count all")
    parser.add_argument("--max-states", type=int, default=1_000_000,
                        help="max expanded states, 0 = unlimited (default 1,000,000)")
    parser.add_argument("--max-queue", type=int, default=2_000_000,
                        help="max queue size, 0 = unlimited (default 2,000,000)")
    parser.add_argument("--time-limit", type=float, default=60.0,
                        help="seconds, 0 = unlimited (default 60)")
    parser.add_argument("--show-path", action="store_true",
                        help="print the sequence of assignments leading to the solution")


def _load_puzzle(args: argparse.Namespace) -> tuple[str, tuple[int, ...]]:
    if args.puzzle is not None:
        return "custom", parse_grid(args.puzzle)
    if args.file is not None:
        try:
            text = args.file.read_text(encoding="utf-8")
        except OSError as error:
            raise SudokuError(f"Cannot read puzzle file: {error}") from error
        return f"file {args.file}", parse_grid(text)
    return args.difficulty, get_puzzle(args.difficulty)


def run(args: argparse.Namespace) -> int:
    try:
        label, puzzle = _load_puzzle(args)
        limits = SearchLimits(
            max_states=args.max_states or None,
            max_queue=args.max_queue or None,
            time_limit=args.time_limit or None,
        )
        solver = SudokuBFS(puzzle, limits, args.order, args.count_solutions)
    except SudokuError as error:
        print(f"Error: {error}")
        return 2

    print(f"Sudoku ({label}) - Breadth First Search with backtracking\n")
    print(format_grid(puzzle))
    print("\nTheoretical landscape:")
    print(format_landscape(compute_theoretical_landscape(puzzle)))

    result = solver.solve()
    validation = validate_solution(result.solution, puzzle) if result.solution else None
    difficulty = (
        classify_difficulty(result.stats)
        if result.solution and args.order == "mrv" and not args.count_solutions
        else None
    )
    print("\nMeasured search statistics:")
    print(format_result(result, validation, difficulty))

    if result.solution is None:
        reason = "the puzzle has no solution" if result.status == "no_solution" \
            else f"search limit reached ({result.stats.limit_reached})"
        print(f"\nNo solution: {reason}.")
        return 1
    print("\nSolution:")
    print(format_grid(result.solution))
    if args.show_path:
        steps = ", ".join(f"r{c // 9 + 1}c{c % 9 + 1}={d}" for c, d in result.path)
        print(f"\nSolution path ({len(result.path)} assignments): {steps}")
    return 0 if validation.is_valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sudoku", description="Sudoku solved with Breadth First Search and backtracking."
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))
