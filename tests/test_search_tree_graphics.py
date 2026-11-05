"""Tests for the graphical search-tree diagrams (SVG / DOT / PNG)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from main import main as project_main
from search_trees import build_search_tree
from search_trees.core import DUPLICATE
from search_trees.graphics import build_drawing, export, render_dot, render_svg
from search_trees.eight_puzzle.model import EightPuzzle
from search_trees.eight_puzzle.model import diagram_style as puzzle_style
from search_trees.missionaries_cannibals.model import MissionariesCannibals
from search_trees.missionaries_cannibals.model import diagram_style as crossing_style
from search_trees.workforce_scheduling.model import RotatingWorkforce
from search_trees.workforce_scheduling.model import diagram_style as workforce_style

SVG = "{http://www.w3.org/2000/svg}"
WORKFORCE = RotatingWorkforce()

# (name, problem, style, strategy, build options, drawing depth, node budget)
# -- the settings that produced the diagrams in docs/assets/search_trees.
CASES = [
    ("eight_puzzle_bfs", EightPuzzle(), puzzle_style(), "bfs", {}, 2, 20),
    ("eight_puzzle_dfs", EightPuzzle(), puzzle_style(), "dfs", {}, 5, 40),
    ("missionaries", MissionariesCannibals(), crossing_style(), "bfs", {"stop_at_goal": False}, 11, 60),
    ("workforce", WORKFORCE, workforce_style(WORKFORCE), "dfs", {}, 2, 20),
]


def make(case):
    _, problem, style, strategy, options, depth, nodes = case
    tree = build_search_tree(problem, strategy, **options)
    return tree, build_drawing(tree, style, depth, nodes)


@pytest.fixture(params=CASES, ids=[c[0] for c in CASES])
def built(request):
    return make(request.param)


class TestDrawing:
    def test_root_is_the_initial_state_at_the_top(self, built):
        tree, drawing = built
        root = drawing.root
        assert root.key == "n0" and root.kind == "start" and root.depth == 0 and root.badge == 1
        assert root.y == min(box.y for box in drawing.boxes)

    def test_goal_and_complete_solution_path_are_drawn(self, built):
        tree, drawing = built
        keys = {box.key: box for box in drawing.boxes}
        assert keys[f"n{tree.goal.id}"].kind == "goal"
        for node in tree.solution_path():
            assert keys[f"n{node.id}"].on_path

    def test_edges_are_real_transitions(self, built):
        tree, drawing = built
        for parent, child in drawing.edges():
            if child.kind == "omitted":
                assert child.key == f"more{parent.node_id}"
                continue
            node = tree.nodes[child.node_id]
            assert node.parent == parent.node_id                  # parent-child link of the tree
            assert child.depth == parent.depth + 1
            assert child.edge_label == drawing.style.edge_label(node.action)

    def test_boxes_show_the_generated_states(self, built):
        tree, drawing = built
        for box in drawing.boxes:
            if box.view is not None:
                node = tree.nodes[box.node_id]
                assert box.view == drawing.style.view(node.state)
                assert box.badge == node.order                    # expansion order of the search

    def test_every_tree_node_is_drawn_counted_or_a_hidden_duplicate(self, built):
        tree, drawing = built
        drawn = sum(1 for box in drawing.boxes if box.view is not None)
        omitted = sum(int(box.label[0].split()[0]) for box in drawing.boxes if box.kind == "omitted")
        assert drawn + omitted + drawing.hidden_duplicates == len(tree.nodes)

    def test_no_overlapping_boxes(self, built):
        _, drawing = built
        boxes = drawing.boxes
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if a.depth == b.depth:
                    assert abs(a.x - b.x) >= (a.width + b.width) / 2, (a.key, b.key)

    def test_captions_state_what_is_drawn(self):
        _, bfs = make(CASES[0])
        _, dfs = make(CASES[1])
        _, crossing = make(CASES[2])
        assert bfs.caption[1].startswith("Partial search tree: 20 of 54 nodes drawn")
        assert dfs.complete and dfs.caption[1] == "Complete search tree: all 16 nodes drawn."
        assert crossing.complete and crossing.hidden_duplicates == 16
        assert "33 of 49 nodes drawn" in crossing.caption[1]


class TestProblemStyles:
    def test_puzzle_nodes_are_boards_with_a_blue_blank(self):
        tree, drawing = make(CASES[1])
        root = drawing.root.view
        assert root.shape == "grid" and root.grid == (("2", "8", "3"), ("1", "6", "4"), ("7", "", "5"))
        assert root.cell_styles[""][0] == "#38bdf8"
        assert drawing.style.caption(next(n for n in tree.nodes if n.status == DUPLICATE)).startswith("repeat of depth")

    def test_crossing_nodes_and_edges_use_the_bracket_notation(self):
        tree, drawing = make(CASES[2])
        assert drawing.root.view.shape == "ellipse" and drawing.root.view.text == "[3, 3, 1]"
        labels = {child.edge_label for _, child in drawing.edges()}
        assert "[0 2 1]" in labels and "[0 1 -1]" in labels
        assert all(box.kind != "duplicate" for box in drawing.boxes)          # hidden, as stated
        assert {b.caption for b in drawing.boxes if b.kind == "invalid"} == {"left bank unsafe", "right bank unsafe"}

    def test_workforce_nodes_are_schedule_grids_with_rule_captions(self):
        _, drawing = make(CASES[3])
        root = drawing.root.view
        assert root.shape == "grid" and len(root.grid) == 3 and len(root.grid[0]) == 7
        assert set(v for row in root.grid for v in row) == {"?"}
        captions = {b.caption for b in drawing.boxes if b.kind == "invalid"}
        assert "R1 demand" in captions and "R6 availability" in captions


class TestFormats:
    def test_svg_is_valid_and_matches_the_drawing(self, built):
        tree, drawing = built
        root = ET.fromstring(render_svg(drawing))
        assert root.tag == f"{SVG}svg"
        groups = {g.get("id"): g for g in root.iter(f"{SVG}g")}
        assert groups["node-n0"].get("data-kind") == "start"
        assert groups[f"node-n{tree.goal.id}"].get("data-kind") == "goal"
        edges = [e.get("id") for e in root.iter(f"{SVG}polyline")]
        assert sorted(edges) == sorted(f"edge-{p.key}-{c.key}" for p, c in drawing.edges())
        texts = " ".join(t.text or "" for t in root.iter(f"{SVG}text"))
        assert "depth 0" in texts and "Legend" in texts and "goal node" in texts

    def test_dot_contains_every_node_and_edge(self, built):
        _, drawing = built
        dot = render_dot(drawing)
        assert dot.startswith("digraph SearchTree {") and dot.rstrip().endswith("}")
        for box in drawing.boxes:
            assert f"  {box.key} [shape=" in dot
        for parent, child in drawing.edges():
            assert f"  {parent.key} -> {child.key} [" in dot

    def test_export_writes_files(self, tmp_path):
        tree, _ = make(CASES[2])
        files = export(tree, crossing_style(), tmp_path / "tree", 1, 10)
        assert {f.name for f in files} >= {"tree.svg", "tree.dot"}
        assert (tmp_path / "tree.svg").read_text(encoding="utf-8").startswith("<svg")

    def test_png_export(self, tmp_path):
        pytest.importorskip("PIL")
        tree, _ = make(CASES[0])
        files = export(tree, puzzle_style(), tmp_path / "tree", 1, 10)
        png = tmp_path / "tree.png"
        assert png in files and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.parametrize("command", [["eight-puzzle", "--strategy", "dfs"], ["missionaries"], ["workforce"]])
    def test_cli_graph_option(self, command, tmp_path, capsys):
        stem = tmp_path / "tree"
        assert project_main([*command, "--graph", str(stem)]) == 0
        assert "Graphical diagram written to" in capsys.readouterr().out
        assert (tmp_path / "tree.svg").exists() and (tmp_path / "tree.dot").exists()
