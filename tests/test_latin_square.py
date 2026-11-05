"""Tests for the Latin Square generator (model, validator, objective, landscape, IDDFS, CLI)."""

from __future__ import annotations

import re
from math import factorial

import pytest

from latin_square import (
    LatinSquareError,
    LatinSquareIDDFS,
    SearchLimits,
    compute_theoretical_landscape,
    empty_grid,
    evaluate,
    format_grid,
    parse_grid,
    reduced_prefill,
    validate_latin_square,
)
from latin_square.landscape import KNOWN_LATIN_SQUARES, KNOWN_REDUCED_SQUARES
from main import main as project_main

# Example output from Detyra1.md for n = 5.
ASSIGNMENT_EXAMPLE = (
    (1, 2, 3, 4, 5),
    (5, 1, 2, 3, 4),
    (4, 5, 1, 2, 3),
    (3, 4, 5, 1, 2),
    (2, 3, 4, 5, 1),
)
# Consistent clues, but no completion: cell (1,2) needs a 3, which column 3 already has.
DEAD_AT_FIRST_CELL = "1 2 ./. . 3/. . ."
# Consistent clues, but no completion: (1,2) must be 2, then (2,1) has no value.
UNSOLVABLE_2X2 = "1 ./. 2"


def solve(n, prefill=None, reduced=None, step=1, count_all=False, **limits):
    if reduced is None:
        reduced = prefill is None
    grid = parse_grid(prefill, n) if isinstance(prefill, str) else prefill
    solver = LatinSquareIDDFS(n, grid, SearchLimits(**limits), step, count_all, reduced)
    return solver, solver.solve()


# ------------------------------------------------------------------ model
class TestModel:
    def test_parse_grid(self):
        grid = parse_grid("1 2 ./. . 1/3,.,.", 3)
        assert grid == ((1, 2, 0), (0, 0, 1), (3, 0, 0))

    @pytest.mark.parametrize("text, n, message", [
        ("1 2/3 4/5 6", 2, "must have 2 rows"),
        ("1 2 3/. .", 2, "Row 1 must have 2 cells"),
        ("1 x/. .", 2, "Invalid cell value"),
        ("1 3/. .", 2, "integers 0..2"),
        ("1 1/. .", 2, "value 1 repeated in row 1"),
        ("1 ./1 .", 2, "value 1 repeated in column 1"),
    ])
    def test_invalid_grids(self, text, n, message):
        with pytest.raises(LatinSquareError, match=message):
            parse_grid(text, n)

    @pytest.mark.parametrize("n", [0, -2, True, 2.0, "3"])
    def test_invalid_sizes(self, n):
        with pytest.raises(LatinSquareError):
            LatinSquareIDDFS(n)

    def test_reduced_prefill(self):
        assert reduced_prefill(3) == ((1, 2, 3), (2, 0, 0), (3, 0, 0))
        assert reduced_prefill(1) == ((1,),)

    def test_format_grid(self):
        assert format_grid(((1, 0), (0, 1))) == "1 .\n. 1"

    @pytest.mark.parametrize("step", [0, -1, 1.5, True])
    def test_invalid_step(self, step):
        with pytest.raises(LatinSquareError, match="step"):
            LatinSquareIDDFS(3, step=step)

    def test_prefill_and_reduced_are_exclusive(self):
        with pytest.raises(LatinSquareError, match="cannot be combined"):
            LatinSquareIDDFS(2, empty_grid(2), reduced=True)

    @pytest.mark.parametrize("kwargs", [{"max_nodes": 0}, {"max_nodes": 2.5}, {"time_limit": 0}, {"time_limit": "1"}])
    def test_invalid_limits(self, kwargs):
        with pytest.raises(LatinSquareError):
            SearchLimits(**kwargs)


# -------------------------------------------------------------- validator
class TestValidator:
    def test_assignment_example_is_valid(self):
        assert validate_latin_square(ASSIGNMENT_EXAMPLE, 5).is_valid

    def test_repeated_value_in_row_and_column(self):
        bad = ((1, 2), (1, 2))
        report = validate_latin_square(bad, 2)
        assert any("Column 1" in e for e in report.errors)
        assert any("Column 2" in e for e in report.errors)
        report = validate_latin_square(((1, 1), (2, 2)), 2)
        assert any("Row 1" in e for e in report.errors)

    @pytest.mark.parametrize("square", [((1, 2),), ((1, 2), (2,)), ((1, 3), (3, 1)), ((0, 1), (1, 0)), None])
    def test_malformed_squares(self, square):
        assert not validate_latin_square(square, 2).is_valid

    def test_prefill_must_be_kept(self):
        prefill = ((2, 0), (0, 0))
        report = validate_latin_square(((1, 2), (2, 1)), 2, prefill)
        assert any("changed from 2 to 1" in e for e in report.errors)


# -------------------------------------------------------------- objective
class TestObjective:
    def test_complete_square(self):
        value = evaluate(ASSIGNMENT_EXAMPLE)
        assert value.phi == 0 and value.is_solution

    def test_empty_and_partial_grids(self):
        assert evaluate(empty_grid(4)).phi == 16
        value = evaluate(reduced_prefill(4))
        assert value.violations == 0 and value.empty_cells == 9

    def test_violations(self):
        # Row 1 has value 1 three times (2 violations); columns are fine.
        value = evaluate(((1, 1, 1), (0, 0, 0), (0, 0, 0)))
        assert value.violations == 2 and not value.is_consistent


# -------------------------------------------------------------- landscape
class TestLandscape:
    def test_formulas_for_full_grid(self):
        land = compute_theoretical_landscape(3, empty_grid(3))
        assert land.free_cells == 9
        assert land.naive_assignments == 3 ** 9
        assert land.row_permutation_bound == 6 ** 3
        assert land.full_tree_nodes == sum(3 ** d for d in range(10))
        assert land.iddfs_unpruned_nodes == sum(sum(3 ** d for d in range(L + 1)) for L in range(10))
        assert land.known_latin_squares == 12

    def test_reduced_grid(self):
        land = compute_theoretical_landscape(5, reduced_prefill(5))
        assert land.free_cells == 16 and land.naive_assignments == 5 ** 16

    def test_literature_constants_are_consistent(self):
        for n, reduced in KNOWN_REDUCED_SQUARES.items():
            assert KNOWN_LATIN_SQUARES[n] == factorial(n) * factorial(n - 1) * reduced


# ------------------------------------------------------------------ IDDFS
class TestIDDFS:
    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
    def test_reduced_form_generates_valid_squares(self, n):
        solver, result = solve(n)
        assert result.status == "solved"
        assert validate_latin_square(result.solution, n, solver.prefill).is_valid

    @pytest.mark.parametrize("n", [1, 2, 3, 4])
    def test_full_grid_generates_valid_squares(self, n):
        _, result = solve(n, reduced=False)
        assert result.status == "solved"
        assert validate_latin_square(result.solution, n).is_valid
        assert result.solution[0] == tuple(range(1, n + 1))  # ascending value order

    def test_full_grid_n5_with_row_step(self):
        solver, result = solve(5, reduced=False, step=5)
        assert solver.depth_limits() == [0, 5, 10, 15, 20, 25]
        assert result.status == "solved" and validate_latin_square(result.solution, 5).is_valid

    @pytest.mark.parametrize("n", [3, 4, 5])
    def test_depth_limits_start_at_zero_and_grow_by_one(self, n):
        solver, result = solve(n)
        free = (n - 1) ** 2
        assert solver.depth_limits() == list(range(free + 1))
        assert [it.depth_limit for it in result.stats.iterations] == list(range(free + 1))

    @pytest.mark.parametrize("n", [3, 4, 5])
    def test_each_iteration_respects_its_depth_limit(self, n):
        _, result = solve(n)
        iterations = result.stats.iterations
        for it in iterations[:-1]:
            assert it.outcome == "cutoff" and it.cutoffs > 0
            assert it.max_depth == it.depth_limit          # never deeper than the limit
        assert iterations[-1].outcome == "found"
        assert iterations[-1].max_depth == result.stats.free_cells

    def test_iterations_restart_from_the_root(self):
        # Every iteration that does not find a goal explores a superset of the
        # previous tree, so its node count never decreases.
        _, result = solve(4, reduced=False)
        counts = [it.nodes_visited for it in result.stats.iterations[:-1]]
        assert counts == sorted(counts)
        assert result.stats.nodes_visited == sum(it.nodes_visited for it in result.stats.iterations)
        assert result.stats.repeated_work_ratio > 1

    @pytest.mark.parametrize("n", [1, 2, 3, 4])
    def test_count_all_matches_literature_full(self, n):
        _, result = solve(n, reduced=False, count_all=True, max_nodes=None)
        assert result.search_completed
        assert result.stats.solutions_found == KNOWN_LATIN_SQUARES[n]

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
    def test_count_all_matches_literature_reduced(self, n):
        _, result = solve(n, count_all=True, max_nodes=None)
        assert result.stats.solutions_found == KNOWN_REDUCED_SQUARES[n]

    def test_unsolvable_prefill_detected_early(self):
        solver, result = solve(3, DEAD_AT_FIRST_CELL)
        assert result.status == "no_solution" and result.search_completed
        # Limit 0 cuts off at the root; limit 1 exhausts the tree without a
        # cutoff, so IDDFS stops instead of trying limits 2..6.
        assert [it.outcome for it in result.stats.iterations] == ["cutoff", "failure"]
        assert len(solver.depth_limits()) == 7
        assert result.stats.dead_ends == 1

    def test_unsolvable_2x2(self):
        _, result = solve(2, UNSOLVABLE_2X2)
        assert result.status == "no_solution" and result.solution is None
        assert result.stats.iterations[-1].outcome == "failure"

    def test_prefill_completion(self):
        prefill = parse_grid(". . 1/. 1 ./1 . .", 3)
        _, result = solve(3, prefill, reduced=False)
        assert result.status == "solved"
        assert validate_latin_square(result.solution, 3, prefill).is_valid

    def test_complete_prefill_is_goal_at_depth_zero(self):
        prefill = parse_grid("1 2/2 1", 2)
        _, result = solve(2, prefill, reduced=False)
        assert result.status == "solved" and result.stats.nodes_visited == 1

    def test_statistics_are_consistent(self):
        _, result = solve(5)
        for it in result.stats.iterations:
            assert it.values_tried == it.rejected_conflicts + it.assignments
            assert it.nodes_visited == it.assignments + 1        # + root
        for it in result.stats.iterations[:-1]:                 # exhausted iterations
            assert it.values_tried == 5 * it.nodes_expanded
        last = result.stats.iterations[-1]                      # stops at the first goal
        assert last.values_tried <= 5 * last.nodes_expanded
        assert last.backtracks == last.assignments - result.stats.free_cells

    def test_node_limit(self):
        _, result = solve(5, reduced=False, max_nodes=1000)
        assert result.status == "limit_reached" and result.stats.limit_reached == "max_nodes"
        assert result.stats.nodes_visited == 1000 and result.stats.iterations[-1].outcome == "limit"

    def test_time_limit(self):
        _, result = solve(6, reduced=False, time_limit=1e-6, max_nodes=None)
        assert result.stats.limit_reached == "time_limit"


# -------------------------------------------------------------------- CLI
class TestCLI:
    @pytest.mark.parametrize("n", [3, 4, 5])
    def test_runs(self, n, capsys):
        assert project_main(["latin", "-n", str(n)]) == 0
        out = capsys.readouterr().out
        assert re.search(r"Independent validation\s+: PASSED", out)
        assert "Nodes explored per depth limit" in out

    def test_full_grid_option(self, capsys):
        assert project_main(["latin", "-n", "3", "--no-symmetry-breaking", "--hide-iterations"]) == 0
        out = capsys.readouterr().out
        assert "(full grid)" in out and "Nodes explored per depth limit" not in out

    def test_count_solutions(self, capsys):
        assert project_main(["latin", "-n", "4", "--count-solutions"]) == 0
        assert re.search(r"Solutions found\s+: 4\n", capsys.readouterr().out)

    def test_unsolvable_prefill_exit_code(self, capsys):
        assert project_main(["latin", "-n", "2", "--prefill", UNSOLVABLE_2X2]) == 1
        assert "No solution: no Latin square completes this grid." in capsys.readouterr().out

    @pytest.mark.parametrize("args, message", [
        (["-n", "0"], "n must be >= 1"),
        (["-n", "2", "--prefill", "1 1/. ."], "repeated in row 1"),
        (["-n", "3", "--step", "0"], "step must be a positive integer"),
    ])
    def test_invalid_input_exit_code(self, args, message, capsys):
        assert project_main(["latin", *args]) == 2
        assert message in capsys.readouterr().out
