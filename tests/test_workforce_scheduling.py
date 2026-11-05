"""Tests for the Rotating Workforce Scheduling search tree."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from main import main as project_main
from search_trees import SearchTreeError, build_search_tree
from search_trees.core import DUPLICATE, INVALID
from search_trees.workforce_scheduling.model import RotatingWorkforce, WorkforceConfig, load_config
from search_trees.workforce_scheduling.validator import validate_schedule

# The schedule the DFS finds for the default configuration (also used to
# break single constraints for the validator tests).
DEFAULT_SOLUTION = [
    list("DDDD---"),
    list("NN-NN-D"),
    list("--N-DD-"),
]


def solve(config=None, strategy="dfs", **kwargs):
    problem = RotatingWorkforce(config)
    return problem, build_search_tree(problem, strategy, **kwargs)


class TestConfig:
    @pytest.mark.parametrize("changes, message", [
        ({"employees": 0}, "employees"),
        ({"shifts": ("D", "D")}, "distinct"),
        ({"shifts": ("D", "-")}, "distinct"),
        ({"demand": {"D": (1,) * 7}}, "one row per shift"),
        ({"demand": {"D": (1,) * 6, "N": (1,) * 7}}, "must list 7"),
        ({"demand": {"D": (2,) * 7, "N": (2,) * 7}}, "exceeds the number of employees"),
        ({"forbidden_sequences": (("N", "X"),)}, "unknown shift"),
        ({"max_consecutive_same": {"X": 2}}, "unknown shift"),
        ({"min_work_per_row": 4, "max_work_per_row": 3}, "max_work_per_row"),
        ({"max_work_per_row": 8}, "cannot exceed days"),
        ({"unavailable": ((5, 0),)}, "out of range"),
    ])
    def test_invalid_configurations(self, changes, message):
        with pytest.raises(SearchTreeError, match=message):
            replace(WorkforceConfig(), **changes)

    def test_blocked_cells_follow_the_rotation(self):
        config = replace(WorkforceConfig(), unavailable=((0, 6), (0, 8), (2, 13)))
        # Employee 1, week 1 Sunday -> row 1 Sunday (0, 6);
        # employee 1, week 2 Tuesday -> row 2 Tuesday (1, 1);
        # employee 3, week 2 Sunday -> row (2 + 1) mod 3 = 1 again, Sunday (0, 6).
        assert config.blocked_cells() == {(0, 6), (1, 1)}

    def test_load_config_round_trip(self, tmp_path):
        path = tmp_path / "rws.json"
        path.write_text(json.dumps({"employees": 3, "max_consecutive_work": 5,
                                    "forbidden_sequences": [["N", "D"], ["N", "-"]]}), encoding="utf-8")
        config = load_config(path)
        assert config.max_consecutive_work == 5
        assert config.forbidden_sequences == (("N", "D"), ("N", "-"))

    def test_load_config_errors(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(SearchTreeError, match="JSON object"):
            load_config(bad)
        with pytest.raises(SearchTreeError, match="Cannot read"):
            load_config(tmp_path / "missing.json")


class TestSearchTree:
    def test_default_schedule_found_and_valid(self):
        problem, tree = solve()
        assert tree.goal is not None and tree.goal.depth == 21
        rows = problem.schedule_rows(tree.goal.state)
        assert rows == DEFAULT_SOLUTION
        assert validate_schedule(rows, problem.config).is_valid

    def test_bfs_finds_the_same_first_schedule_depth(self):
        problem, tree = solve(strategy="bfs")
        assert tree.goal.depth == 21
        assert validate_schedule(problem.schedule_rows(tree.goal.state), problem.config).is_valid
        _, dfs_tree = solve()
        assert tree.stats.nodes_generated > dfs_tree.stats.nodes_generated

    def test_invalid_nodes_have_reasons_and_are_not_expanded(self):
        _, tree = solve()
        invalid = [n for n in tree.nodes if n.status == INVALID]
        assert invalid and all(n.reason.startswith("R") and not n.children for n in invalid)

    def test_cell_order_makes_duplicates_impossible(self):
        _, tree = solve(strategy="bfs", max_depth=8, stop_at_goal=False)
        assert not any(n.status == DUPLICATE for n in tree.nodes)

    def test_each_constraint_can_reject(self):
        _, tree = solve(strategy="bfs", stop_at_goal=False, max_nodes=200_000)
        reasons = {n.reason.split()[0] for n in tree.nodes if n.status == INVALID}
        assert {"R1", "R2", "R3", "R4", "R5", "R6"} <= reasons

    def test_unsatisfiable_configuration(self):
        # 12 working cells cannot give each of 3 rows at least 5 working days.
        config = replace(WorkforceConfig(), min_work_per_row=5)
        _, tree = solve(config)
        assert tree.goal is None and tree.stats.limit_reached is None

    def test_explore_all_counts_schedules(self):
        problem, tree = solve(stop_at_goal=False)
        assert tree.stats.goals_found >= 1
        for goal_id in tree.goal_ids:
            rows = problem.schedule_rows(tree.nodes[goal_id].state)
            assert validate_schedule(rows, problem.config).is_valid

    def test_employee_view_rotates_rows(self):
        problem, tree = solve()
        view = problem.employee_view(tree.goal.state).splitlines()
        assert view[0] == "Employee 1: DDDD--- | NN-NN-D | --N-DD-"
        assert view[1] == "Employee 2: NN-NN-D | --N-DD- | DDDD---"


class TestValidator:
    config = WorkforceConfig()

    def broken(self, row, day, value):
        rows = [r[:] for r in DEFAULT_SOLUTION]
        rows[row][day] = value
        return validate_schedule(rows, self.config).errors

    def test_valid(self):
        assert validate_schedule(DEFAULT_SOLUTION, self.config).is_valid

    def test_shape_and_values(self):
        assert validate_schedule(DEFAULT_SOLUTION[:2], self.config).errors
        assert any("unknown shift" in e for e in self.broken(0, 0, "X"))

    def test_demand(self):
        assert any("demand" in e for e in self.broken(0, 4, "D"))

    def test_forbidden_sequence_including_wrap_around(self):
        assert any("Forbidden sequence N->D" in e for e in self.broken(1, 5, "N"))
        # last day of row 3 followed by the first day of row 1 (cyclic)
        assert any("N->D" in e for e in self.broken(2, 6, "N"))

    def test_runs_workload_and_availability(self):
        config = replace(self.config, max_consecutive_work=3)
        assert any("Working run" in e for e in validate_schedule(DEFAULT_SOLUTION, config).errors)
        config = replace(self.config, max_consecutive_same={"N": 1})
        assert any("N shifts" in e for e in validate_schedule(DEFAULT_SOLUTION, config).errors)
        config = replace(self.config, max_work_per_row=4)
        assert any("working days" in e for e in validate_schedule(DEFAULT_SOLUTION, config).errors)
        config = replace(self.config, unavailable=((0, 0),))
        assert any("unavailable" in e for e in validate_schedule(DEFAULT_SOLUTION, config).errors)


class TestCLI:
    def test_default_run(self, capsys, tmp_path):
        diagram = tmp_path / "rws.md"
        assert project_main(["workforce", "--mermaid", str(diagram)]) == 0
        out = capsys.readouterr().out
        assert "Independent validation: PASSED" in out and "Employee 3:" in out
        assert "flowchart TD" in diagram.read_text(encoding="utf-8")

    def test_unsatisfiable_config_file(self, capsys, tmp_path):
        path = tmp_path / "rws.json"
        path.write_text(json.dumps({"min_work_per_row": 5}), encoding="utf-8")
        assert project_main(["workforce", "--config", str(path)]) == 1
        assert "cannot all be satisfied" in capsys.readouterr().out

    def test_invalid_config_file(self, capsys, tmp_path):
        path = tmp_path / "rws.json"
        path.write_text(json.dumps({"employees": 0}), encoding="utf-8")
        assert project_main(["workforce", "--config", str(path)]) == 2
