"""Tests for the Sudoku solver (model, validator, objective, landscape, BFS, CLI)."""

from __future__ import annotations

import re

import pytest

from main import main as project_main
from sudoku import (
    SearchLimits,
    SudokuBFS,
    SudokuError,
    check_puzzle,
    classify_difficulty,
    compute_theoretical_landscape,
    evaluate,
    get_puzzle,
    parse_grid,
    validate_solution,
)
from sudoku.puzzles import EXTRA_PUZZLES, PUZZLES

EASY = PUZZLES["easy"]
EASY_SOLUTION = (
    "534678912672195348198342567859761423426853791"
    "713924856961537284287419635345286179"
)
# The easy solution with a "deadly rectangle" (r1c4, r1c5, r4c4, r4c5) emptied:
# the two digits can be swapped, so the puzzle has exactly 2 solutions.
TWO_SOLUTIONS = "534..8912672195348198342567859..1423426853791713924856961537284287419635345286179"
# Consistent clues, but r1c9 has no legal digit (1-8 in its row, 9 in its column).
UNSOLVABLE_AT_ROOT = "12345678." + "........9" + "." * 63
# The hard puzzle plus one extra clue (2 at r1c2): no clue conflicts, but the
# search has to explore thousands of states to prove there is no solution.
UNSOLVABLE_DEEP = "82.........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."


def solve(puzzle: str, order: str = "mrv", count_all: bool = False, **limits):
    grid = parse_grid(puzzle)
    return grid, SudokuBFS(grid, SearchLimits(**limits), order, count_all).solve()


# ---------------------------------------------------------------- parsing
class TestParsingAndInitialValidation:
    def test_parse_single_line(self):
        grid = parse_grid(EASY)
        assert len(grid) == 81 and grid[0] == 5 and grid[2] == 0

    def test_parse_drawing_with_separators(self):
        lines = [EASY[i:i + 9] for i in range(0, 81, 9)]
        drawing = "\n".join(f"{l[:3]} | {l[3:6]} | {l[6:]}" for l in lines)
        assert parse_grid(drawing.replace(".", "0")) == parse_grid(EASY)

    @pytest.mark.parametrize("text, message", [
        ("123", "must have 81 cells"),
        ("x" + "." * 80, "Invalid character"),
        ("." * 82, "must have 81 cells"),
    ])
    def test_malformed_puzzles(self, text, message):
        with pytest.raises(SudokuError, match=message):
            parse_grid(text)

    def test_non_string_rejected(self):
        with pytest.raises(SudokuError):
            parse_grid(123)

    @pytest.mark.parametrize("puzzle, unit", [
        ("55" + "." * 79, "row 1"),
        ("5" + "." * 8 + "5" + "." * 71, "column 1"),
        ("5" + "." * 9 + "5" + "." * 70, "box 1"),
    ])
    def test_conflicting_clues_rejected(self, puzzle, unit):
        with pytest.raises(SudokuError, match=f"digit 5 repeated in {unit}"):
            SudokuBFS(parse_grid(puzzle))

    @pytest.mark.parametrize("bad", [(0,) * 80, (10,) + (0,) * 80, (True,) + (0,) * 80, [0] * 81])
    def test_check_puzzle_rejects_bad_grids(self, bad):
        with pytest.raises(SudokuError):
            check_puzzle(bad)

    def test_invalid_variable_order_and_limits(self):
        with pytest.raises(SudokuError, match="variable_order"):
            SudokuBFS(parse_grid(EASY), variable_order="random")
        for kwargs in ({"max_states": 0}, {"max_queue": -1}, {"time_limit": 0}, {"max_states": 1.5}):
            with pytest.raises(SudokuError):
                SearchLimits(**kwargs)


# -------------------------------------------------------------- validator
class TestValidator:
    def test_valid_solution(self):
        report = validate_solution(parse_grid(EASY_SOLUTION), parse_grid(EASY))
        assert report.is_valid, report.errors

    def test_changed_clue_detected(self):
        puzzle = list(parse_grid(EASY))
        puzzle[0] = 4  # pretend the clue at r1c1 was 4
        report = validate_solution(parse_grid(EASY_SOLUTION), tuple(puzzle))
        assert any("Clue at r1c1 changed" in e for e in report.errors)

    def test_swapped_cells_break_rows_columns_or_boxes(self):
        bad = list(parse_grid(EASY_SOLUTION))
        bad[0], bad[9] = bad[9], bad[0]  # swap r1c1 and r2c1
        report = validate_solution(bad)
        assert any("Row 1" in e for e in report.errors)
        assert any("Row 2" in e for e in report.errors)

    @pytest.mark.parametrize("bad", [[1] * 80, [0] * 81, ["1"] * 81, None])
    def test_malformed_solutions(self, bad):
        assert not validate_solution(bad).is_valid


# -------------------------------------------------------------- objective
class TestObjective:
    def test_solution_has_phi_zero(self):
        value = evaluate(parse_grid(EASY_SOLUTION))
        assert value.phi == 0 and value.is_solution

    def test_puzzle_is_consistent_partial_state(self):
        value = evaluate(parse_grid(EASY))
        assert value.violations == 0 and value.empty_cells == 51 and value.phi == 51
        assert value.is_consistent and not value.is_solution

    def test_violations_are_counted_per_unit(self):
        # Two 5s at r1c1, r1c2: 1 extra copy in row 1 + 1 in box 1.
        # Three 7s at r1c9, r2c9, r3c9: 2 extra copies in column 9 + 2 in box 3
        # (row 1 then holds one 5 and one 7, no repeat).
        grid = ["."] * 81
        grid[0] = grid[1] = "5"
        grid[8] = grid[17] = grid[26] = "7"
        value = evaluate(parse_grid("".join(grid)))
        assert value.violations == (1 + 1) + (2 + 2)
        assert not value.is_consistent


# -------------------------------------------------------------- landscape
class TestLandscape:
    def test_easy_landscape(self):
        land = compute_theoretical_landscape(parse_grid(EASY))
        assert land.clues == 30 and land.empty_cells == 51
        assert land.naive_bound == 9 ** 51
        assert land.domain_product_bound <= land.naive_bound
        assert 1 <= land.min_domain_size <= land.average_domain_size <= land.max_domain_size <= 9

    def test_complete_grid_has_trivial_landscape(self):
        land = compute_theoretical_landscape(parse_grid(EASY_SOLUTION))
        assert land.empty_cells == 0 and land.naive_bound == 1 and land.domain_product_bound == 1

    def test_empty_grid(self):
        land = compute_theoretical_landscape(parse_grid("." * 81))
        assert land.domain_product_bound == 9 ** 81 and land.total_candidates == 729

    def test_two_solution_puzzle_domains(self):
        land = compute_theoretical_landscape(parse_grid(TWO_SOLUTIONS))
        assert land.empty_cells == 4 and land.domain_product_bound == 2 ** 4


# ------------------------------------------------------------- BFS solver
class _RecordingBFS(SudokuBFS):
    """Records the depth of every expanded state, in expansion order."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expanded_depths = []

    def _expand(self, node):
        self.expanded_depths.append(node.depth)
        yield from super()._expand(node)


class TestBFSSolver:
    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_predefined_puzzles_are_solved_and_validated(self, difficulty):
        grid = get_puzzle(difficulty)
        result = SudokuBFS(grid).solve()
        assert result.status == "solved"
        assert validate_solution(result.solution, grid).is_valid

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_measured_difficulty_matches_label(self, difficulty):
        result = SudokuBFS(get_puzzle(difficulty)).solve()
        assert classify_difficulty(result.stats) == difficulty

    @pytest.mark.parametrize("puzzle", list(PUZZLES.values()) + list(EXTRA_PUZZLES.values()))
    def test_puzzles_have_a_unique_solution(self, puzzle):
        _, result = solve(puzzle, count_all=True)
        assert result.search_completed and result.stats.solutions_found == 1

    def test_effort_grows_with_difficulty(self):
        effort = [SudokuBFS(get_puzzle(d)).solve().stats for d in ("easy", "medium", "hard")]
        assert effort[0].states_expanded < effort[1].states_expanded < effort[2].states_expanded
        assert effort[0].backtracks == 0 < effort[1].backtracks < effort[2].backtracks
        assert effort[0].max_queue_size < effort[1].max_queue_size < effort[2].max_queue_size

    def test_bfs_expands_states_in_fifo_level_order(self):
        for order in ("mrv", "row-major"):
            solver = _RecordingBFS(get_puzzle("medium"), variable_order=order, count_all=True)
            result = solver.solve()
            depths = solver.expanded_depths
            assert depths == sorted(depths), "a deeper state was expanded before a shallower one"
            assert len(depths) == result.stats.states_expanded
            # Every level is fully expanded before the next one starts.
            levels = [depths.count(d) for d in range(max(depths) + 1)]
            assert levels == result.stats.frontier_per_depth[: len(levels)]

    def test_multiple_solutions_found_at_same_depth(self):
        grid, result = solve(TWO_SOLUTIONS, count_all=True)
        assert result.stats.solutions_found == 2
        assert len(set(result.solutions)) == 2
        assert all(validate_solution(s, grid).is_valid for s in result.solutions)
        assert result.stats.frontier_per_depth[-1] == 2  # both goals at depth E = 4

    def test_first_solution_mode_stops_early(self):
        _, result = solve(TWO_SOLUTIONS)
        assert result.status == "solved" and result.stats.solutions_found == 1

    def test_unsolvable_at_root(self):
        _, result = solve(UNSOLVABLE_AT_ROOT)
        assert result.status == "no_solution" and result.search_completed
        assert result.stats.states_expanded == 0 and result.solution is None

    def test_unsolvable_after_search(self):
        grid, result = solve(UNSOLVABLE_DEEP)
        check_puzzle(grid)  # clues alone are consistent
        assert result.status == "no_solution" and result.search_completed
        assert result.stats.states_expanded > 1000 and result.stats.backtracks > 0

    def test_already_solved_puzzle(self):
        _, result = solve(EASY_SOLUTION)
        assert result.status == "solved" and result.stats.states_expanded == 0
        assert result.path == []

    def test_solution_path_rebuilds_solution(self):
        grid, result = solve(PUZZLES["hard"])
        assert len(result.path) == 60
        rebuilt = list(grid)
        for cell, digit in result.path:
            assert rebuilt[cell] == 0
            rebuilt[cell] = digit
        assert tuple(rebuilt) == result.solution

    def test_both_variable_orders_agree(self):
        _, mrv = solve(PUZZLES["medium"])
        _, row_major = solve(PUZZLES["medium"], order="row-major")
        assert mrv.solution == row_major.solution
        assert mrv.stats.states_expanded < row_major.stats.states_expanded

    def test_statistics_are_consistent(self):
        for order in ("mrv", "row-major"):
            _, result = solve(PUZZLES["hard"], order=order, count_all=True, max_states=50_000)
            s = result.stats
            assert s.candidates_tested == 9 * s.states_expanded
            assert s.candidates_tested == (
                s.rejected_conflicts + s.pruned_dead_ends + s.states_generated + s.duplicates_skipped
            )
            assert sum(s.frontier_per_depth) == s.states_generated + 1  # + root
            assert s.duplicates_skipped == 0
            assert s.raw_branching_factor == pytest.approx(9.0)
            assert s.effective_branching_factor <= s.consistent_branching_factor <= 9

    def test_mrv_dead_ends_only_at_forced_cells(self):
        # With MRV, a dead end can only occur at a cell with one candidate,
        # so each pruned child causes exactly one failed expansion.
        _, result = solve(PUZZLES["hard"])
        assert result.stats.pruned_dead_ends == result.stats.failed_expansions > 0

    def test_state_limit(self):
        _, result = solve(PUZZLES["hard"], max_states=500)
        assert result.status == "limit_reached" and result.stats.limit_reached == "max_states"
        assert result.stats.states_expanded == 500 and not result.search_completed

    def test_queue_limit(self):
        _, result = solve(PUZZLES["hard"], order="row-major", max_queue=100)
        assert result.stats.limit_reached == "max_queue"

    def test_time_limit(self):
        _, result = solve(PUZZLES["hard"], order="row-major", time_limit=1e-6)
        assert result.stats.limit_reached == "time_limit"

    def test_unknown_difficulty(self):
        with pytest.raises(SudokuError, match="Unknown difficulty"):
            get_puzzle("expert")


# -------------------------------------------------------------------- CLI
class TestCLI:
    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_difficulty_runs(self, difficulty, capsys):
        assert project_main(["sudoku", "-d", difficulty]) == 0
        out = capsys.readouterr().out
        assert re.search(rf"Measured difficulty\s+: {difficulty}", out)
        assert re.search(r"Independent validation\s+: PASSED", out)

    def test_custom_puzzle_file(self, tmp_path, capsys):
        path = tmp_path / "puzzle.txt"
        path.write_text(PUZZLES["medium"], encoding="utf-8")
        assert project_main(["sudoku", "--file", str(path), "--show-path"]) == 0
        assert "Solution path (54 assignments)" in capsys.readouterr().out

    def test_invalid_puzzle_exit_code(self, capsys):
        assert project_main(["sudoku", "--puzzle", "55" + "." * 79]) == 2
        assert "Error: Invalid puzzle: digit 5 repeated in row 1" in capsys.readouterr().out

    def test_missing_file(self, tmp_path, capsys):
        assert project_main(["sudoku", "--file", str(tmp_path / "missing.txt")]) == 2
        assert "Cannot read puzzle file" in capsys.readouterr().out

    def test_unsolvable_exit_code(self, capsys):
        assert project_main(["sudoku", "--puzzle", UNSOLVABLE_AT_ROOT]) == 1
        assert "No solution: the puzzle has no solution." in capsys.readouterr().out

    def test_count_solutions(self, capsys):
        assert project_main(["sudoku", "--puzzle", TWO_SOLUTIONS, "--count-solutions"]) == 0
        assert re.search(r"Solutions found\s+: 2", capsys.readouterr().out)
