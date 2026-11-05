"""Tests for the Missionaries and Cannibals search tree."""

from __future__ import annotations

import pytest

from main import main as project_main
from search_trees import SearchTreeError, build_search_tree
from search_trees.core import INVALID
from search_trees.missionaries_cannibals.model import MissionariesCannibals
from search_trees.missionaries_cannibals.validator import validate_solution, validate_state


def bfs(m=3, c=3, b=2, **kwargs):
    problem = MissionariesCannibals(m, c, b)
    return problem, build_search_tree(problem, "bfs", **kwargs)


class TestModel:
    @pytest.mark.parametrize("args", [(-1, 3, 2), (3, 3, 0), (0, 0, 2), (True, 3, 2), (1, 2, 2)])
    def test_invalid_configurations(self, args):
        with pytest.raises(SearchTreeError):
            MissionariesCannibals(*args)

    def test_states_and_safety(self):
        p = MissionariesCannibals()
        assert p.initial_state() == (3, 3, 1) and p.goal_state() == (0, 0, 0)
        assert p.is_safe((3, 1, 0)) and p.is_safe((0, 3, 1)) and p.is_safe((1, 1, 0))
        assert not p.is_safe((2, 3, 0))      # left: 3 cannibals > 2 missionaries
        assert not p.is_safe((1, 0, 0))      # right: 3 cannibals > 2 missionaries

    def test_boat_loads(self):
        assert MissionariesCannibals().boat_loads() == [(0, 1), (0, 2), (1, 0), (1, 1), (2, 0)]

    def test_expand_marks_unsafe_crossings(self):
        moves = MissionariesCannibals().expand((3, 3, 1))
        valid = {t.action for t in moves if t.valid}
        invalid = {t.action: t.reason for t in moves if not t.valid}
        assert valid == {"0M1C to R", "0M2C to R", "1M1C to R"}
        assert invalid == {"1M0C to R": "left bank: 3 cannibals > 2 missionaries",
                           "2M0C to R": "left bank: 3 cannibals > 1 missionaries"}

    def test_moves_never_take_absent_people(self):
        p = MissionariesCannibals()
        for state in p.all_states():
            for move in p.expand(state):
                assert p.in_range(move.state)


class TestSearchTree:
    def test_classic_solution(self):
        problem, tree = bfs()
        assert tree.goal.depth == 11
        report = validate_solution(tree.solution_states(), 3, 3, 2)
        assert report.is_valid, report.errors

    def test_dfs_solution_is_valid(self):
        problem = MissionariesCannibals()
        tree = build_search_tree(problem, "dfs")
        assert tree.goal is not None
        assert validate_solution(tree.solution_states(), 3, 3, 2).is_valid

    def test_reachable_state_space(self):
        problem, tree = bfs(stop_at_goal=False)
        safe = [s for s in problem.all_states() if not validate_state(s, 3, 3)]
        assert len(problem.all_states()) == 32 and len(safe) == 20
        assert tree.stats.unique_states == 15        # reachable safe states (measured)
        assert tree.stats.limit_reached is None

    def test_invalid_states_are_never_expanded(self):
        _, tree = bfs(stop_at_goal=False)
        invalid = [n for n in tree.nodes if n.status == INVALID]
        assert invalid and all(not n.children for n in invalid)
        assert all(validate_state(n.state, 3, 3) for n in invalid)
        valid = [n for n in tree.nodes if n.status != INVALID]
        assert all(not validate_state(n.state, 3, 3) for n in valid)

    def test_four_four_two_has_no_solution(self):
        _, tree = bfs(4, 4, 2)
        assert tree.goal is None and tree.stats.limit_reached is None

    @pytest.mark.parametrize("m, c, b", [(1, 1, 2), (2, 2, 2), (4, 4, 3), (5, 5, 3)])
    def test_other_solvable_configurations(self, m, c, b):
        _, tree = bfs(m, c, b)
        assert tree.goal is not None
        assert validate_solution(tree.solution_states(), m, c, b).is_valid


class TestValidator:
    def test_state_errors(self):
        assert validate_state((3, 3, 1), 3, 3) == []
        assert validate_state((4, 0, 1), 3, 3)
        assert validate_state((2, 3, 1), 3, 3)
        assert validate_state((3, 3, 2), 3, 3)
        assert validate_state("x", 3, 3)

    def test_path_errors(self):
        assert not validate_solution([], 3, 3, 2).is_valid
        report = validate_solution([(3, 3, 1), (3, 3, 0)], 3, 3, 2)
        assert any("must end at" in e for e in report.errors)
        report = validate_solution([(3, 3, 1), (0, 0, 0)], 3, 3, 2)
        assert any("capacity 2" in e for e in report.errors)
        report = validate_solution([(3, 3, 1), (3, 1, 1)], 3, 3, 2)
        assert any("change sides" in e for e in report.errors)


class TestCLI:
    def test_default_run(self, capsys):
        assert project_main(["missionaries"]) == 0
        out = capsys.readouterr().out
        assert "Solution (11 crossings)" in out and "Independent validation: PASSED" in out
        assert "invalid; left bank: 3 cannibals > 2 missionaries" in out

    def test_unsolvable_configuration(self, capsys):
        assert project_main(["missionaries", "-m", "4", "-c", "4"]) == 1
        assert "No solution found." in capsys.readouterr().out

    def test_invalid_configuration(self, capsys):
        assert project_main(["missionaries", "-m", "1", "-c", "2"]) == 2
        assert "Initial state is unsafe" in capsys.readouterr().out
