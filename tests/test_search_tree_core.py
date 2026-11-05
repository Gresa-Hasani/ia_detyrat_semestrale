"""Tests for the shared search-tree engine and its visualizations."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from search_trees import SearchTreeError, Transition, build_search_tree, render_mermaid, render_text
from search_trees.core import DEAD_END, DEPTH_LIMIT, DUPLICATE, EXPANDED, FRONTIER, GOAL, INVALID


@dataclass
class ToyGraph:
    """Small graph with a cycle, an invalid move and two goals.

        A -> B, C, X(invalid)    B -> A, D    C -> D, E    D -> G    E -> G2
    """

    edges = {
        "A": [("ab", "B"), ("ac", "C"), ("ax", None)],
        "B": [("ba", "A"), ("bd", "D")],
        "C": [("cd", "D"), ("ce", "E")],
        "D": [("dg", "G")],
        "E": [("eg", "G2")],
        "G": [],
        "G2": [],
    }

    def initial_state(self):
        return "A"

    def is_goal(self, state):
        return state in ("G", "G2")

    def expand(self, state):
        return [
            Transition(action, target) if target else Transition(action, "X", valid=False, reason="blocked")
            for action, target in self.edges[state]
        ]

    def format_state(self, state):
        return state

    def format_label(self, state):
        return state


def statuses(tree):
    return {node.state: node.status for node in tree.nodes if node.status != DUPLICATE}


class TestBuildSearchTree:
    def test_bfs_finds_shallowest_goal_and_records_parents(self):
        tree = build_search_tree(ToyGraph(), "bfs")
        assert tree.goal.state == "G" and tree.goal.depth == 3
        assert tree.solution_actions() == ["ab", "bd", "dg"]
        assert tree.solution_states() == ["A", "B", "D", "G"]
        for node in tree.nodes[1:]:
            assert node.id in tree.nodes[node.parent].children
            assert node.depth == tree.nodes[node.parent].depth + 1

    def test_bfs_expands_level_by_level(self):
        tree = build_search_tree(ToyGraph(), "bfs", stop_at_goal=False)
        expanded = [n.depth for n in tree.nodes if n.status in (EXPANDED, DEAD_END)]
        assert expanded == sorted(expanded)

    def test_dfs_follows_first_action_first(self):
        tree = build_search_tree(ToyGraph(), "dfs")
        assert tree.solution_actions() == ["ab", "bd", "dg"]
        graph, order = ToyGraph(), []
        original = graph.expand
        graph.expand = lambda state: order.append(state) or original(state)
        build_search_tree(graph, "dfs", stop_at_goal=False)
        assert order[:4] == ["A", "B", "D", "C"]          # depth first: B's subtree before C

    def test_duplicate_detection(self):
        tree = build_search_tree(ToyGraph(), "bfs", stop_at_goal=False)
        dups = [n for n in tree.nodes if n.status == DUPLICATE]
        assert {n.state for n in dups} == {"A", "D"}       # B -> A, and the second path to D
        assert all(not n.children for n in dups)
        assert tree.stats.duplicates == 2
        assert tree.stats.unique_states == 7                # A B C D E G G2

    def test_invalid_transitions_are_leaves(self):
        tree = build_search_tree(ToyGraph(), "bfs")
        invalid = [n for n in tree.nodes if n.status == INVALID]
        assert len(invalid) == 1 and invalid[0].reason == "blocked" and not invalid[0].children
        assert tree.stats.invalid_transitions == 1
        tree = build_search_tree(ToyGraph(), "bfs", record_invalid=False)
        assert all(n.status != INVALID for n in tree.nodes) and tree.stats.invalid_transitions == 1

    def test_explore_all_finds_every_goal(self):
        tree = build_search_tree(ToyGraph(), "bfs", stop_at_goal=False)
        assert tree.stats.goals_found == 2
        assert {tree.nodes[i].state for i in tree.goal_ids} == {"G", "G2"}

    def test_depth_limit(self):
        tree = build_search_tree(ToyGraph(), "bfs", max_depth=1)
        assert tree.goal is None and tree.stats.max_depth == 1
        assert statuses(tree)["B"] == DEPTH_LIMIT and statuses(tree)["C"] == DEPTH_LIMIT

    def test_tree_search_without_duplicate_detection(self):
        tree = build_search_tree(ToyGraph(), "bfs", max_depth=4, duplicate_detection=False,
                                 stop_at_goal=False)
        assert tree.stats.duplicates == 0
        assert sum(1 for n in tree.nodes if n.state == "A") > 1   # the cycle is expanded again

    def test_node_and_time_limits(self):
        tree = build_search_tree(ToyGraph(), "bfs", max_nodes=3)
        assert tree.stats.limit_reached == "max_nodes"
        assert any(n.status == FRONTIER for n in tree.nodes)
        tree = build_search_tree(ToyGraph(), "bfs", time_limit=1e-9)
        assert tree.stats.limit_reached == "time_limit"

    def test_goal_at_root(self):
        graph = ToyGraph()
        graph.initial_state = lambda: "G"
        tree = build_search_tree(graph)
        assert tree.goal.id == 0 and tree.nodes[0].status == GOAL and tree.stats.nodes_expanded == 0

    @pytest.mark.parametrize("kwargs", [
        {"strategy": "astar"}, {"max_depth": -1}, {"max_nodes": 0}, {"time_limit": 0}, {"max_nodes": 2.5},
    ])
    def test_invalid_parameters(self, kwargs):
        with pytest.raises(SearchTreeError):
            build_search_tree(ToyGraph(), **kwargs)

    def test_statistics_identities(self):
        tree = build_search_tree(ToyGraph(), "bfs", stop_at_goal=False)
        s = tree.stats
        assert s.transitions_examined == s.valid_transitions + s.invalid_transitions
        assert s.nodes_generated == len(tree.nodes) == 1 + s.transitions_examined
        assert s.raw_branching_factor >= s.valid_branching_factor >= s.effective_branching_factor


class TestVisualization:
    def test_text_tree_marks_statuses(self):
        tree = build_search_tree(ToyGraph(), "bfs")
        text = render_text(tree, str, max_depth=5, max_nodes=50)
        assert "[0] d=0 A  (INITIAL; on solution path)" in text
        assert "invalid; blocked" in text and "GOAL" in text and "duplicate" in text
        assert "(Complete tree:" in text

    def test_text_tree_is_depth_limited(self):
        tree = build_search_tree(ToyGraph(), "bfs")
        text = render_text(tree, str, max_depth=1, max_nodes=50)
        assert "d=2" not in text and "Partial view" in text

    def test_mermaid_structure(self):
        tree = build_search_tree(ToyGraph(), "bfs", stop_at_goal=False)
        diagram = render_mermaid(tree, str, max_depth=5, max_nodes=50, title="toy")
        lines = diagram.splitlines()
        assert lines[0] == "flowchart TD" and "%% toy" in lines[1]
        edges = [l for l in lines if "-->" in l]
        assert len(edges) == len(tree.nodes) - 1
        assert '-->|"ab"|' in diagram
        assert "class n0 start" in diagram and "class partialNote" not in diagram
        for status_class in ("goal", "duplicate", "invalid", "path"):
            assert f" {status_class}" in diagram

    def test_mermaid_partial_note(self):
        tree = build_search_tree(ToyGraph(), "bfs")
        diagram = render_mermaid(tree, str, max_depth=1, max_nodes=50)
        assert "Partial tree:" in diagram and "depth at most 1" in diagram
