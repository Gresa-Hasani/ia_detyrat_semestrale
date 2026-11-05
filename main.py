"""Entry point for Assignment 1 (uninformed search techniques).

Usage examples:
    python main.py golfers --groups 8 --size 4
    python main.py golfers -g 3 -p 2 --count-solutions
    python main.py sudoku --difficulty hard
    python main.py latin -n 5
    python main.py eight-puzzle
    python main.py missionaries
    python main.py workforce
"""

from __future__ import annotations

import argparse
import sys

from social_golfers import cli as golfers_cli
from latin_square import cli as latin_cli
from search_trees import cli as trees_cli
from sudoku import cli as sudoku_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assignment 1: classical uninformed search algorithms."
    )
    problems = parser.add_subparsers(dest="problem", required=True, metavar="PROBLEM")
    golfers = problems.add_parser(
        "golfers", help="Social Golfers Problem (DFS with backtracking)"
    )
    golfers_cli.add_arguments(golfers)
    golfers.set_defaults(handler=golfers_cli.run)

    sudoku = problems.add_parser(
        "sudoku", help="Sudoku solver (BFS with backtracking)"
    )
    sudoku_cli.add_arguments(sudoku)
    sudoku.set_defaults(handler=sudoku_cli.run)

    latin = problems.add_parser(
        "latin", help="Latin Square generator (IDDFS with backtracking)"
    )
    latin_cli.add_arguments(latin)
    latin.set_defaults(handler=latin_cli.run)

    for name, help_text, add, run in (
        ("eight-puzzle", "Search tree: 8-Puzzle",
         trees_cli.add_eight_puzzle_arguments, trees_cli.run_eight_puzzle),
        ("missionaries", "Search tree: Missionaries and Cannibals",
         trees_cli.add_missionaries_arguments, trees_cli.run_missionaries),
        ("workforce", "Search tree: Rotating Workforce Scheduling",
         trees_cli.add_workforce_arguments, trees_cli.run_workforce),
    ):
        sub = problems.add_parser(name, help=help_text)
        add(sub)
        sub.set_defaults(handler=run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
