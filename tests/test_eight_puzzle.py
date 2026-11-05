"""Tests for the 8-Puzzle search tree."""

from __future__ import annotations

import pytest

from main import main as project_main
from search_trees import SearchTreeError, build_search_tree
from search_trees.eight_puzzle.model import (
    DEFAULT_GOAL,
    DEFAULT_INITIAL,
    REACHABLE_BOARDS,
    EightPuzzle,
    apply_move,
    inversions,
    is_solvable,
    parse_board,
)
from search_trees.eight_puzzle.validator import validate_solution

GOAL_BLANK_LAST = (1, 2, 3, 4, 5, 6, 7, 8, 0)


class TestModel:
    def test_parse_board(self):
        assert parse_board("2 8 3 / 1 6 4 / 7 _ 5") == DEFAULT_INITIAL
        assert parse_board("1,2,3,8,0,4,7,6,5") == DEFAULT_GOAL

    @pytest.mark.parametrize("text", ["1 2 3", "1 1 2 3 4 5 6 7 8", "1 2 3 4 5 6 7 8 9", "a 2 3 4 5 6 7 8 0"])
    def test_invalid_boards(self, text):
        with pytest.raises(SearchTreeError):
            parse_board(text)

    def test_invalid_problem(self):
        with pytest.raises(SearchTreeError):
            EightPuzzle(initial=(1, 2, 3))

    @pytest.mark.parametrize("blank, count", [(0, 2), (2, 2), (6, 2), (8, 2), (1, 3), (3, 3), (5, 3), (7, 3), (4, 4)])
    def test_legal_actions_depend_on_blank_position(self, blank, count):
        board = [1, 2, 3, 4, 5, 6, 7, 8]
        board.insert(blank, 0)
        assert len(EightPuzzle().legal_actions(tuple(board))) == count

    def test_apply_move(self):
        assert apply_move(DEFAULT_INITIAL, "Up") == (2, 8, 3, 1, 0, 4, 7, 6, 5)
        assert apply_move(DEFAULT_INITIAL, "Down") is None          # blank on the bottom row
        with pytest.raises(SearchTreeError):
            apply_move(DEFAULT_INITIAL, "Jump")

    def test_inversions_and_solvability(self):
        assert inversions(GOAL_BLANK_LAST) == 0
        assert inversions((2, 1, 3, 4, 5, 6, 7, 8, 0)) == 1
        assert is_solvable(DEFAULT_INITIAL, DEFAULT_GOAL)
        assert not is_solvable((2, 1, 3, 4, 5, 6, 7, 8, 0), GOAL_BLANK_LAST)

    def test_moves_preserve_inversion_parity(self):
        tree = build_search_tree(EightPuzzle(), "bfs", max_depth=6, stop_at_goal=False)
        parity = inversions(DEFAULT_INITIAL) % 2
        assert all(inversions(node.state) % 2 == parity for node in tree.nodes)


class TestSearchTree:
    def test_bfs_finds_shortest_solution(self):
        problem = EightPuzzle()
        tree = build_search_tree(problem, "bfs")
        assert tree.goal.depth == 5
        assert tree.solution_actions() == ["Up", "Up", "Left", "Down", "Right"]
        assert validate_solution(problem.initial, problem.goal, tree.solution_actions()).is_valid

    def test_dfs_finds_a_valid_solution(self):
        problem = EightPuzzle(parse_board("1 2 3 / 4 5 6 / 0 7 8"), GOAL_BLANK_LAST)
        tree = build_search_tree(problem, "dfs", max_nodes=500_000)
        assert tree.goal is not None
        assert validate_solution(problem.initial, problem.goal, tree.solution_actions()).is_valid
        bfs = build_search_tree(problem, "bfs")
        assert bfs.goal.depth == 2 <= tree.goal.depth

    def test_parent_child_relationships(self):
        tree = build_search_tree(EightPuzzle(), "bfs")
        for node in tree.nodes[1:]:
            parent = tree.nodes[node.parent]
            assert apply_move(parent.state, node.action) == node.state
            assert node.depth == parent.depth + 1

    def test_duplicates_are_detected(self):
        tree = build_search_tree(EightPuzzle(), "bfs")
        assert tree.stats.duplicates > 0
        states = [n.state for n in tree.nodes if n.status != "duplicate"]
        assert len(states) == len(set(states))

    def test_already_solved(self):
        tree = build_search_tree(EightPuzzle(DEFAULT_GOAL, DEFAULT_GOAL))
        assert tree.goal.depth == 0 and tree.solution_actions() == []

    def test_full_state_space_of_unsolvable_instance(self):
        # Swapping two tiles flips the parity: BFS exhausts all 181,440
        # reachable boards without finding the goal.
        problem = EightPuzzle((2, 1, 3, 4, 5, 6, 7, 8, 0), GOAL_BLANK_LAST)
        tree = build_search_tree(problem, "bfs", max_nodes=None)
        assert tree.goal is None and tree.stats.limit_reached is None
        assert tree.stats.unique_states == REACHABLE_BOARDS

    def test_branching_factor_statistics(self):
        tree = build_search_tree(EightPuzzle(), "bfs")
        s = tree.stats
        assert 2 <= s.raw_branching_factor <= 4
        assert s.effective_branching_factor < s.valid_branching_factor


class TestValidator:
    def test_illegal_move(self):
        report = validate_solution(DEFAULT_INITIAL, DEFAULT_GOAL, ["Down"])
        assert any("leaves the board" in e for e in report.errors)

    def test_wrong_final_board(self):
        report = validate_solution(DEFAULT_INITIAL, DEFAULT_GOAL, ["Up"])
        assert any("differs from goal" in e for e in report.errors)

    def test_unknown_action_and_bad_boards(self):
        assert not validate_solution(DEFAULT_INITIAL, DEFAULT_GOAL, ["Jump"]).is_valid
        assert not validate_solution((1, 2), DEFAULT_GOAL, []).is_valid


class TestCLI:
    def test_default_run(self, capsys, tmp_path):
        out_file = tmp_path / "tree.md"
        assert project_main(["eight-puzzle", "--mermaid", str(out_file)]) == 0
        out = capsys.readouterr().out
        assert "Solution (5 moves of the blank): Up, Up, Left, Down, Right" in out
        assert "Independent validation: PASSED" in out
        text = out_file.read_text(encoding="utf-8")
        assert text.startswith("```mermaid\nflowchart TD") and text.rstrip().endswith("```")

    def test_custom_unsolvable(self, capsys):
        args = ["eight-puzzle", "--initial", "2 1 3 4 5 6 7 8 0", "--goal", "1 2 3 4 5 6 7 8 0",
                "--max-depth", "4"]
        assert project_main(args) == 1
        out = capsys.readouterr().out
        assert "Solvable (same inversion parity): no" in out and "No solution found" in out

    def test_invalid_board(self, capsys):
        assert project_main(["eight-puzzle", "--initial", "1 2 3"]) == 2
        assert "Error:" in capsys.readouterr().out

    def test_tree_search_needs_depth_limit(self, capsys):
        assert project_main(["eight-puzzle", "--no-duplicate-detection"]) == 2
        assert "needs --max-depth" in capsys.readouterr().out
