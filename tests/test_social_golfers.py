"""Tests for the Social Golfers Problem (model, validator, objective, landscape, DFS, CLI)."""

from __future__ import annotations

import re
from math import comb, factorial

import pytest

from main import main as project_main
from social_golfers.report import format_big
from social_golfers import (
    ConfigurationError,
    GolferConfig,
    SearchLimits,
    SocialGolfersDFS,
    compute_theoretical_landscape,
    objective_value,
    repeated_pair_violations,
    validate_schedule,
)

# Week 1 of the example table in Detyra1.md (n=32, g=8, p=4).
ASSIGNMENT_EXAMPLE_WEEK = [
    [0, 1, 2, 3], [4, 5, 22, 23], [6, 7, 20, 21], [8, 25, 26, 27],
    [9, 10, 11, 24], [12, 13, 15, 30], [14, 28, 29, 31], [16, 17, 18, 19],
]

# A hand-written complete 3-week schedule for n=4, g=2, p=2 (all matchings of K4).
K4_SCHEDULE = [[[0, 1], [2, 3]], [[0, 2], [1, 3]], [[0, 3], [1, 2]]]


def solve(g, p, weeks=None, max_nodes=2_000_000, symmetry=True, count_all=False):
    config = GolferConfig(g, p)
    result = SocialGolfersDFS(
        config, weeks, SearchLimits(max_nodes=max_nodes), symmetry, count_all
    ).solve()
    return config, result


# ---------------------------------------------------------------- model
class TestConfiguration:
    def test_basic_properties(self):
        config = GolferConfig(8, 4)
        assert config.num_golfers == 32
        assert config.week_upper_bound == 10  # floor(31 / 3)

    @pytest.mark.parametrize(
        "g, p, bound", [(2, 2, 3), (3, 2, 5), (3, 3, 4), (4, 4, 5), (4, 3, 5), (2, 3, 1), (1, 4, 1)]
    )
    def test_week_upper_bound(self, g, p, bound):
        assert GolferConfig(g, p).week_upper_bound == bound

    def test_golfers_must_equal_g_times_p(self):
        with pytest.raises(ConfigurationError, match="n must equal g x p"):
            GolferConfig.from_parameters(8, 4, golfers=30)
        assert GolferConfig.from_parameters(8, 4, golfers=32).num_golfers == 32

    @pytest.mark.parametrize(
        "g, p", [(0, 4), (-1, 4), (8, 1), (8, 0), (True, 4), (8, "4"), (2.5, 2)]
    )
    def test_invalid_parameters_are_rejected(self, g, p):
        with pytest.raises(ConfigurationError):
            GolferConfig(g, p)

    @pytest.mark.parametrize("weeks", [0, -3, "2"])
    def test_invalid_target_weeks(self, weeks):
        with pytest.raises(ConfigurationError):
            SocialGolfersDFS(GolferConfig(2, 2), target_weeks=weeks)

    @pytest.mark.parametrize(
        "kwargs", [{"max_nodes": 0}, {"max_nodes": -5}, {"time_limit": 0}, {"time_limit": "x"}]
    )
    def test_invalid_limits(self, kwargs):
        with pytest.raises(ConfigurationError):
            SearchLimits(**kwargs)


# ------------------------------------------------------------ validator
class TestValidator:
    def test_assignment_example_week_is_valid(self):
        report = validate_schedule([ASSIGNMENT_EXAMPLE_WEEK], GolferConfig(8, 4))
        assert report.is_valid, report.errors
        assert report.pairs_checked == 8 * comb(4, 2)

    def test_complete_k4_schedule_is_valid(self):
        assert validate_schedule(K4_SCHEDULE, GolferConfig(2, 2), expected_weeks=3).is_valid

    def test_repeated_pair_detected(self):
        schedule = [[[0, 1], [2, 3]], [[0, 1], [2, 3]]]
        report = validate_schedule(schedule, GolferConfig(2, 2))
        assert not report.is_valid
        assert report.repeated_pairs == {(0, 1): 2, (2, 3): 2}

    def test_wrong_number_of_groups(self):
        report = validate_schedule([[[0, 1, 2, 3]]], GolferConfig(2, 2))
        assert any("groups, expected 2" in e for e in report.errors)

    def test_wrong_group_size(self):
        report = validate_schedule([[[0, 1, 2], [3]]], GolferConfig(2, 2))
        assert any("has 3 golfers" in e for e in report.errors)
        assert any("has 1 golfers" in e for e in report.errors)

    def test_missing_and_duplicate_golfer(self):
        report = validate_schedule([[[0, 1], [1, 2]]], GolferConfig(2, 2))
        assert any("golfer 3 is missing" in e for e in report.errors)
        assert any("golfer 1 appears 2 times" in e for e in report.errors)

    def test_out_of_range_and_non_integer_ids(self):
        report = validate_schedule([[[0, 9], [2, "x"]]], GolferConfig(2, 2))
        assert any("outside 0..3" in e for e in report.errors)
        assert any("not an integer" in e for e in report.errors)

    def test_malformed_structures(self):
        config = GolferConfig(2, 2)
        assert not validate_schedule("nope", config).is_valid
        assert not validate_schedule([5], config).is_valid
        assert not validate_schedule([[5, [2, 3]]], config).is_valid

    def test_expected_weeks_mismatch(self):
        report = validate_schedule(K4_SCHEDULE[:2], GolferConfig(2, 2), expected_weeks=3)
        assert any("expected 3" in e for e in report.errors)


# ------------------------------------------------------------ objective
class TestObjective:
    def test_feasible_schedule(self):
        config = GolferConfig(2, 2)
        assert objective_value(K4_SCHEDULE, config) == 3
        assert repeated_pair_violations(K4_SCHEDULE) == 0

    def test_longest_valid_prefix(self):
        config = GolferConfig(2, 2)
        schedule = K4_SCHEDULE[:2] + [K4_SCHEDULE[0]]  # week 3 repeats week 1
        assert objective_value(schedule, config) == 2
        assert repeated_pair_violations(schedule) == 2

    def test_invalid_first_week_scores_zero(self):
        assert objective_value([[[0, 1, 2, 3]]], GolferConfig(2, 2)) == 0


# ------------------------------------------------------------ landscape
class TestLandscape:
    @pytest.mark.parametrize("g, p, partitions", [(2, 2, 3), (3, 2, 15), (3, 3, 280), (2, 3, 10)])
    def test_partitions_per_week(self, g, p, partitions):
        land = compute_theoretical_landscape(GolferConfig(g, p), 1)
        assert land.partitions_per_week == partitions

    def test_full_instance_formulas(self):
        land = compute_theoretical_landscape(GolferConfig(8, 4), 10)
        partitions = factorial(32) // (factorial(4) ** 8 * factorial(8))
        assert land.partitions_per_week == partitions
        assert land.partition_schedules == partitions ** 10
        assert land.canonical_schedules_bound == comb(partitions - 1, 9)
        assert land.naive_assignments == 32 ** 320
        assert land.permutation_schedules == factorial(32) ** 10
        assert land.total_pairs == 496
        assert land.pairs_used_per_week == 48
        assert land.search_depth == 320
        assert land.search_depth_with_fixed_week == 288
        assert land.max_branching_factor == 31

    def test_invalid_weeks(self):
        with pytest.raises(ConfigurationError):
            compute_theoretical_landscape(GolferConfig(2, 2), 0)


# ------------------------------------------------------------- DFS search
class TestDFSSolver:
    @pytest.mark.parametrize("g, p, weeks", [(2, 2, 3), (3, 2, 5), (3, 3, 4), (4, 4, 5), (5, 2, 9)])
    def test_reaches_theoretical_optimum(self, g, p, weeks):
        config, result = solve(g, p)
        assert result.best_weeks == weeks == config.week_upper_bound
        assert result.target_reached and result.proven_maximum
        assert validate_schedule(result.schedule, config, expected_weeks=weeks).is_valid

    @pytest.mark.parametrize("symmetry", [True, False])
    def test_specific_target(self, symmetry):
        config, result = solve(3, 3, weeks=2, symmetry=symmetry)
        assert result.best_weeks == 2 and result.target_reached
        assert validate_schedule(result.schedule, config, expected_weeks=2).is_valid

    @pytest.mark.parametrize(
        "g, p, symmetry, expected",
        [
            # K4 has 3 perfect matchings -> 3! ordered schedules, 1 canonical one.
            (2, 2, False, 6),
            (2, 2, True, 1),
            # K6 has 6 one-factorizations -> 6 * 5! = 720 ordered schedules;
            # each perfect matching lies in exactly 2 of them -> 2 canonical.
            (3, 2, False, 720),
            (3, 2, True, 2),
        ],
    )
    def test_exhaustive_solution_counts(self, g, p, symmetry, expected):
        _, result = solve(g, p, symmetry=symmetry, count_all=True)
        assert result.search_completed
        assert result.stats.solutions_found == expected

    @pytest.mark.parametrize("g, p", [(2, 3), (2, 4)])
    def test_unsolvable_target_proves_maximum(self, g, p):
        # p > g: by pigeonhole a second week is impossible.
        config, result = solve(g, p, weeks=2)
        assert not result.target_reached
        assert result.search_completed and result.proven_maximum
        assert result.best_weeks == 1
        assert validate_schedule(result.schedule, config).is_valid

    def test_exhaustive_search_proves_four_three_maximum(self):
        # 12 golfers in 4 groups of 3: bound is 5 weeks, exhaustive DFS proves 4.
        config, result = solve(4, 3, max_nodes=None)
        assert result.search_completed
        assert result.best_weeks == 4 and not result.target_reached
        assert result.proven_maximum
        assert validate_schedule(result.schedule, config, expected_weeks=4).is_valid

    def test_full_instance_within_node_limit(self):
        config, result = solve(8, 4, max_nodes=50_000)
        assert result.stats.limit_reached == "max_nodes"
        assert not result.search_completed and not result.proven_maximum
        assert result.best_weeks >= 4
        assert validate_schedule(result.schedule, config, expected_weeks=result.best_weeks).is_valid

    def test_node_limit_terminates(self):
        _, result = solve(4, 3, max_nodes=100)
        assert result.stats.states_expanded == 100
        assert result.stats.limit_reached == "max_nodes"

    def test_time_limit_terminates(self):
        config = GolferConfig(8, 4)
        result = SocialGolfersDFS(
            config, limits=SearchLimits(max_nodes=None, time_limit=1e-6)
        ).solve()
        assert result.stats.limit_reached == "time_limit"
        assert validate_schedule(result.schedule, config).is_valid

    def test_single_week_target(self):
        config, result = solve(8, 4, weeks=1)
        assert result.best_weeks == 1 and result.stats.states_expanded == 0
        assert result.schedule == [[list(range(k * 4, k * 4 + 4)) for k in range(8)]]

    def test_symmetry_breaking_preserves_optimum_and_saves_work(self):
        _, with_sb = solve(3, 2, count_all=True, symmetry=True)
        _, without_sb = solve(3, 2, count_all=True, symmetry=False)
        assert with_sb.best_weeks == without_sb.best_weeks == 5
        assert with_sb.stats.states_expanded < without_sb.stats.states_expanded

    def test_statistics_are_consistent(self):
        _, result = solve(4, 3, max_nodes=20_000)
        s = result.stats
        rejected = (
            s.rejected_pair_conflict + s.rejected_symmetry
            + s.rejected_forward_check + s.rejected_week_check
        )
        assert s.candidates_generated == s.assignments + rejected
        assert sum(s.nodes_per_week) == s.assignments
        assert s.backtracks <= s.assignments
        assert s.fitness_evaluations >= result.best_weeks
        assert 0 < s.candidate_validity_ratio <= 1
        assert s.effective_branching_factor <= s.raw_branching_factor

    def test_schedules_are_canonical(self):
        _, result = solve(4, 4)
        for week in result.schedule:
            assert all(group == sorted(group) for group in week)
            assert [group[0] for group in week] == sorted(group[0] for group in week)


# -------------------------------------------------------------------- CLI
class TestReport:
    def test_format_big_handles_huge_integers(self):
        assert format_big(999) == "999"
        assert format_big(32 ** 320) == "4.446e+481 (482 digits)"


class TestCLI:
    def test_runs_and_prints_schedule(self, capsys):
        assert project_main(["golfers", "-g", "3", "-p", "3"]) == 0
        out = capsys.readouterr().out
        assert "Best schedule (4 weeks)" in out
        assert re.search(r"Independent validation\s+: PASSED", out)

    def test_full_instance_cli(self, capsys):
        assert project_main(["golfers", "-g", "8", "-p", "4", "--max-nodes", "2000"]) == 0
        out = capsys.readouterr().out
        assert re.search(r"Naive assignments n\^\(n\*w\)\s+: \S+e\+481", out)
        assert re.search(r"Search completed\s+: no \(max_nodes\)", out)

    def test_count_solutions(self, capsys):
        assert project_main(["golfers", "-g", "3", "-p", "2", "--count-solutions"]) == 0
        assert re.search(r"Solutions counted\s+: 2\n", capsys.readouterr().out)

    def test_invalid_configuration_exit_code(self, capsys):
        assert project_main(["golfers", "-g", "8", "-p", "4", "-n", "30"]) == 2
        assert "Error: n must equal g x p" in capsys.readouterr().out

    def test_target_beyond_bound_warns(self, capsys):
        assert project_main(["golfers", "-g", "2", "-p", "3", "-w", "2"]) == 0
        assert "Warning: target exceeds" in capsys.readouterr().out
