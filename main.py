"""Entry point for Assignment 1 (uninformed search techniques).

Usage examples:
    python main.py golfers --groups 8 --size 4
    python main.py golfers -g 3 -p 2 --count-solutions
"""

from __future__ import annotations

import argparse
import sys

from social_golfers import cli as golfers_cli


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
