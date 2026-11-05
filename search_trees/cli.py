"""Command-line interface for the three search-tree problems."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import STRATEGIES, SearchTreeError, build_search_tree
from .eight_puzzle.model import (
    AVERAGE_BRANCHING_FACTOR,
    DEFAULT_GOAL,
    DEFAULT_INITIAL,
    REACHABLE_BOARDS,
    TOTAL_BOARDS,
    EightPuzzle,
    format_board,
    inversions,
    parse_board,
)
from .eight_puzzle.model import diagram_style as puzzle_style
from .eight_puzzle.validator import validate_solution as validate_puzzle
from .missionaries_cannibals.model import MissionariesCannibals
from .missionaries_cannibals.model import diagram_style as crossing_style
from .missionaries_cannibals.validator import validate_solution as validate_crossing
from .missionaries_cannibals.validator import validate_state
from .graphics import export
from .report import format_stats
from .visualization import render_mermaid, render_text
from .workforce_scheduling.model import RotatingWorkforce, WorkforceConfig, load_config
from .workforce_scheduling.model import diagram_style as workforce_style
from .workforce_scheduling.validator import validate_schedule


# --------------------------------------------------------------- shared options
def _add_common(parser: argparse.ArgumentParser, strategy: str) -> None:
    parser.add_argument("--strategy", choices=STRATEGIES, default=strategy,
                        help=f"tree construction order (default {strategy})")
    parser.add_argument("--max-depth", type=int, default=None, help="do not expand nodes at this depth")
    parser.add_argument("--max-nodes", type=int, default=1_000_000,
                        help="max tree nodes, 0 = unlimited (default 1,000,000)")
    parser.add_argument("--time-limit", type=float, default=60.0, help="seconds, 0 = unlimited (default 60)")
    parser.add_argument("--no-duplicate-detection", action="store_true",
                        help="tree search: expand repeated states again (use with --max-depth)")
    parser.add_argument("--explore-all", action="store_true",
                        help="keep building the tree after the first goal")
    parser.add_argument("--tree-depth", type=int, default=3, help="depth shown in the tree view (default 3)")
    parser.add_argument("--tree-nodes", type=int, default=40, help="max nodes shown in the tree view (default 40)")
    parser.add_argument("--mermaid", type=Path, help="write a depth-limited Mermaid diagram to this file")
    parser.add_argument("--graph", type=Path, metavar="STEM",
                        help="write a graphical diagram: STEM.svg, STEM.dot (Graphviz) and STEM.png "
                             "(PNG only if Pillow is installed)")
    parser.add_argument("--no-solution-path", action="store_true",
                        help="draw only the depth-limited part (by default the whole solution path "
                             "and the alternatives at each step are added)")


def _build(problem, args):
    if args.no_duplicate_detection and args.max_depth is None:
        raise SearchTreeError("--no-duplicate-detection needs --max-depth (the tree would be infinite)")
    for name in ("tree_depth", "tree_nodes"):
        if getattr(args, name) < (0 if name == "tree_depth" else 1):
            raise SearchTreeError(f"--{name.replace('_', '-')} is too small")
    return build_search_tree(
        problem,
        strategy=args.strategy,
        max_depth=args.max_depth,
        max_nodes=args.max_nodes or None,
        time_limit=args.time_limit or None,
        duplicate_detection=not args.no_duplicate_detection,
        stop_at_goal=not args.explore_all,
    )


def _show_tree(problem, tree, args, title: str, style) -> None:
    path = not args.no_solution_path
    scope = " plus the solution path" if path and tree.goal_ids else ""
    print(f"\nSearch tree (nodes up to depth {args.tree_depth}, at most {args.tree_nodes}{scope}):")
    print(render_text(tree, problem.format_state, args.tree_depth, args.tree_nodes, path))
    if args.mermaid:
        diagram = render_mermaid(tree, problem.format_label, args.tree_depth, args.tree_nodes, title, path)
        args.mermaid.write_text(f"```mermaid\n{diagram}\n```\n", encoding="utf-8")
        print(f"\nMermaid diagram written to {args.mermaid}")
    if args.graph:
        files = export(tree, style, args.graph, args.tree_depth, args.tree_nodes, path)
        print("\nGraphical diagram written to " + ", ".join(str(f) for f in files))
    print("\nSearch statistics:")
    print(format_stats(tree))


def _fail(error: Exception) -> int:
    print(f"Error: {error}")
    return 2


# ------------------------------------------------------------------- 8-Puzzle
def add_eight_puzzle_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--initial", default=format_board(DEFAULT_INITIAL),
                        help="initial board, 9 tiles row by row, 0 or _ = blank")
    parser.add_argument("--goal", default=format_board(DEFAULT_GOAL), help="goal board")
    _add_common(parser, "bfs")


def run_eight_puzzle(args: argparse.Namespace) -> int:
    try:
        problem = EightPuzzle(parse_board(args.initial), parse_board(args.goal))
        print("8-Puzzle search tree")
        print(f"  Initial: {format_board(problem.initial)}  (inversions {inversions(problem.initial)})")
        print(f"  Goal:    {format_board(problem.goal)}  (inversions {inversions(problem.goal)})")
        print(f"  Boards: {TOTAL_BOARDS:,} in total, {REACHABLE_BOARDS:,} reachable from any board; "
              f"average branching factor {AVERAGE_BRANCHING_FACTOR:.3f}")
        print(f"  Solvable (same inversion parity): {'yes' if problem.solvable else 'no'}")
        tree = _build(problem, args)
    except SearchTreeError as error:
        return _fail(error)
    title = f"8-Puzzle search tree ({tree.strategy.upper()})"
    _show_tree(problem, tree, args, title, puzzle_style(title))
    if tree.goal is None:
        print("\nNo solution found" + (" (search limit reached)." if tree.stats.limit_reached else "."))
        return 1
    actions = tree.solution_actions()
    report = validate_puzzle(problem.initial, problem.goal, actions)
    print(f"\nSolution ({len(actions)} moves of the blank): {', '.join(actions) or '(already solved)'}")
    for node in tree.solution_path():
        print(f"  d={node.depth}: {format_board(node.state)}")
    print(f"Independent validation: {'PASSED' if report.is_valid else 'FAILED'}")
    return 0 if report.is_valid else 1


# ------------------------------------------------- Missionaries and Cannibals
def add_missionaries_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-m", "--missionaries", type=int, default=3, help="missionaries (default 3)")
    parser.add_argument("-c", "--cannibals", type=int, default=3, help="cannibals (default 3)")
    parser.add_argument("-b", "--capacity", type=int, default=2, help="boat capacity (default 2)")
    _add_common(parser, "bfs")


def run_missionaries(args: argparse.Namespace) -> int:
    try:
        problem = MissionariesCannibals(args.missionaries, args.cannibals, args.capacity)
        tree = _build(problem, args)
    except SearchTreeError as error:
        return _fail(error)
    states = problem.all_states()
    safe = [s for s in states if not validate_state(s, problem.missionaries, problem.cannibals)]
    print(f"Missionaries and Cannibals: {problem.missionaries} missionaries, {problem.cannibals} cannibals, "
          f"boat capacity {problem.capacity}")
    print(f"  State (m, c, boat) with m, c on the LEFT bank; initial {problem.initial_state()}, "
          f"goal {problem.goal_state()}")
    print(f"  State space: {len(states)} combinations, {len(safe)} safe; "
          f"{len(problem.boat_loads())} possible boat loads")
    title = f"Missionaries and Cannibals search tree ({tree.strategy.upper()})"
    _show_tree(problem, tree, args, title, crossing_style(title))
    if tree.goal is None:
        print("\nNo solution found" + (" (search limit reached)." if tree.stats.limit_reached else "."))
        return 1
    report = validate_crossing(tree.solution_states(), problem.missionaries, problem.cannibals,
                               problem.capacity)
    print(f"\nSolution ({len(tree.solution_actions())} crossings):")
    for node in tree.solution_path():
        print(f"  d={node.depth:>2} {node.action or 'start':<10} {problem.format_state(node.state)}")
    print(f"Independent validation: {'PASSED' if report.is_valid else 'FAILED'}")
    for error in report.errors:
        print(f"  - {error}")
    return 0 if report.is_valid else 1


# ---------------------------------------------------- Workforce scheduling
def add_workforce_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="JSON configuration (default: built-in example)")
    _add_common(parser, "dfs")


def run_workforce(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config) if args.config else WorkforceConfig()
        problem = RotatingWorkforce(config)
        tree = _build(problem, args)
    except SearchTreeError as error:
        return _fail(error)
    print(f"Rotating Workforce Scheduling: {config.employees} employees, {config.days} days per week, "
          f"shifts {', '.join(config.shifts)} and '-' (off)")
    print(f"  Search depth: {config.cells} cells; naive assignments {len(problem.values)}^{config.cells} = "
          f"{len(problem.values) ** config.cells:,}")
    title = f"Rotating Workforce Scheduling search tree ({tree.strategy.upper()})"
    _show_tree(problem, tree, args, title, workforce_style(problem, title))
    if tree.goal is None:
        print("\nNo schedule found" + (" (search limit reached)." if tree.stats.limit_reached
                                       else ": the constraints cannot all be satisfied."))
        return 1
    rows = problem.schedule_rows(tree.goal.state)
    report = validate_schedule(rows, config)
    print("\nBase schedule (row = week of the rotation):")
    print(problem.format_schedule(tree.goal.state))
    print("\nRotation (each employee moves to the next row every week):")
    print(problem.employee_view(tree.goal.state))
    print(f"Independent validation: {'PASSED' if report.is_valid else 'FAILED'}")
    for error in report.errors:
        print(f"  - {error}")
    return 0 if report.is_valid else 1
