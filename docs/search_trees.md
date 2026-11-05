# Problem 4 — Search Trees (overview and shared engine)

The assignment text for this problem is a single sentence: *construct a search
tree for the problems 8-Puzzle, Missionaries and Cannibals and Rotating
Workforce Scheduling.* It does not prescribe a search algorithm, so the trees
are built with the uninformed strategies of this assignment's topic: Breadth
First Search (BFS, default for the 8-Puzzle and Missionaries and Cannibals)
and Depth First Search (DFS, default for workforce scheduling). Both can be
selected for every problem with `--strategy`.

Detailed documentation per problem:

* [8-Puzzle](eight_puzzle.md)
* [Missionaries and Cannibals](missionaries_cannibals.md)
* [Rotating Workforce Scheduling](workforce_scheduling.md) — includes the list
  of assumptions, because the assignment does not define this problem's
  constraints.

Numbers marked **measured** come from running this implementation
(Python 3.13.1, Windows 11); times depend on the machine, all other values are
deterministic.

## 1. Search-tree terminology used in this project

| Term | Meaning in the implementation |
|---|---|
| State | a problem configuration (board, river banks, partial schedule) |
| Node | an element of the tree: state + parent link + action + depth + status |
| Root / initial state | node 0 |
| Action / transition | the edge from a parent to a child, labelled with the action |
| Expansion | generating all transitions of a node |
| Goal node | a node whose state passes the goal test |
| Duplicate | a valid child whose state was already generated at the same or a smaller depth; kept as a leaf, never expanded (graph search) |
| Invalid node | a child produced by a transition that breaks a constraint (e.g. an unsafe crossing); kept as a leaf with the reason, never expanded |
| Depth-limit leaf | a node at `--max-depth`; not expanded |
| Dead end | an expanded node with no new valid child |
| Branching factor | raw: transitions per expanded node; valid: valid transitions per expanded node; effective: new (non-duplicate) children per expanded node |

## 2. The shared engine — [`search_trees/core.py`](../search_trees/core.py)

Each problem implements four functions: `initial_state()`, `is_goal(state)`,
`expand(state)` (returns every transition, valid or invalid with a reason) and
`format_state(state)`. `build_search_tree(problem, strategy, …)` then:

```
function BUILD_SEARCH_TREE(problem, strategy, max_depth, limits):
    root ← NODE(problem.initial_state(), parent = none, depth = 0)
    if GOAL(root): return tree
    frontier ← [root]                 // FIFO queue for BFS, LIFO stack for DFS
    best_depth[root.state] ← 0
    while frontier not empty and limits not reached:
        node ← POP_FRONT(frontier) if BFS else POP_BACK(frontier)
        if node.depth = max_depth: mark DEPTH-LIMIT; continue
        mark node EXPANDED
        for transition in problem.expand(node.state):
            if transition is invalid:
                add INVALID leaf child (with reason); continue
            if duplicate detection and best_depth[state] ≤ node.depth + 1:
                add DUPLICATE leaf child; continue
            best_depth[state] ← node.depth + 1
            child ← add child node (parent = node, action, depth + 1)
            if GOAL(child): record goal; stop unless --explore-all
            new_children.append(child)
        if no new child: mark DEAD-END
        add new_children to frontier (reversed for DFS, so the first action is explored first)
    return tree (all nodes with parent links, statistics, goal ids)
```

Every node keeps its parent id, the action on the incoming edge, its depth and
its list of children, so the solution path is recovered by following parent
links from the goal to the root. The goal test is applied when a node is
generated.

**Duplicate detection** (graph search) can be switched off with
`--no-duplicate-detection`; a `--max-depth` is then required because the tree
of a problem with reversible moves is infinite.

**Limits:** `--max-depth`, `--max-nodes` (tree nodes, default 1,000,000) and
`--time-limit` (default 60 s).

## 3. Visualization — [`visualization.py`](../search_trees/visualization.py), [`graphics.py`](../search_trees/graphics.py)

Search trees grow exponentially, so a drawing never shows more than a
readable part of the tree. Every view is built from the tree that the search
actually generated (no state or edge is invented) and uses the same node
selection:

1. all nodes up to `--tree-depth` (breadth-first, at most `--tree-nodes`);
2. the **complete solution path** from the root to the first goal, however
   deep, together with **all children of every path node** (the alternatives
   the search generated at each step) — `--no-solution-path` turns this off;
3. for every drawn node whose children are not all drawn, a marker
   "k more nodes not drawn", so an omitted branch can never be mistaken for a
   leaf of the search tree.

Each view states whether it shows the complete tree ("Complete tree: all N
nodes shown") or a partial one ("Partial tree: k of N nodes shown (depth at
most d plus the solution path)").

Output formats:

| Option | Output |
|---|---|
| always | **text tree**: one line per node, `[id] d=depth action -> state (status; reason)` |
| `--graph STEM` | **graphical diagram**: `STEM.svg`, `STEM.png` and `STEM.dot` (see below) |
| `--mermaid FILE` | Mermaid `flowchart TD` (same selection, statuses as classes, reasons in italics) |

### Graphical diagrams

`graphics.py` lays the tree out top-down and writes:

* **SVG**, written with the Python standard library only;
* **PNG** at 2× resolution for PDF and print, drawn with Pillow when it is
  installed. Pillow is optional; without it the PNG is skipped;
* **DOT** (Graphviz source) of the same nodes, edges and styles, so the diagram
  can also be laid out by Graphviz: `dot -Tsvg STEM.dot -o STEM_graphviz.svg`.
  Graphviz is not needed by the project and was not installed on the
  development machine, so the committed images use the built-in layout.

Each problem defines how its states are drawn (`diagram_style` in its
`model.py`):

| Problem | Node | Edge label | Notes |
|---|---|---|---|
| 8-Puzzle | the 3×3 board, blank cell in blue | move of the blank (`Up`, `Down`, `Left`, `Right`) | repeated boards say at which depth they were first generated |
| Missionaries and Cannibals | ellipse `[m, c, b]` (left bank, boat side) | `[x y d]`: x missionaries, y cannibals, d = 1 to the right, −1 to the left | killed nodes name the unsafe bank; repeated-state leaves are left out and counted in the caption |
| Rotating Workforce Scheduling | 3 × 7 colour grid of the base schedule (D, N, -, ?) | one cell assignment, e.g. `r2 Tue=N` | killed nodes name the broken rule (R1–R6) |

Common styles: green = processed (expanded) node, blue frame = initial state,
gold = goal node, red = killed node (constraint violated), light blue = no new
child possible, grey dashed = repeated state, white = generated but not
expanded, white dashed box = omitted branch with its node count. The orange
number on a node is the order in which the search expanded it, thick green
arrows mark the solution path, and the ruler on the left gives the depth.
Every image has a legend and a caption saying whether the tree is complete or
partial.

Layout: one row per search depth; children are centred under their parent,
and sibling subtrees are packed with a contour-based tidy-tree algorithm (in
the spirit of Reingold and Tilford), so boxes never overlap and a deep
solution path does not widen the drawing. Edges leave a parent vertically
below the tallest node of its level before they slant towards the child, so
they never cross nodes of the same level.

The committed diagrams are in [`docs/assets/search_trees/`](assets/search_trees/):

| Problem | Diagram | Shown |
|---|---|---|
| 8-Puzzle, DFS | [SVG](assets/search_trees/eight_puzzle_dfs_tree.svg) · [PNG](assets/search_trees/eight_puzzle_dfs_tree.png) · [DOT](assets/search_trees/eight_puzzle_dfs_tree.dot) | complete: all 16 nodes, goal at depth 5 |
| 8-Puzzle, BFS | [SVG](assets/search_trees/eight_puzzle_tree.svg) · [PNG](assets/search_trees/eight_puzzle_tree.png) · [DOT](assets/search_trees/eight_puzzle_tree.dot) | partial: 20 of 54 nodes (depth ≤ 2 plus the 5-move solution path) |
| Missionaries and Cannibals, BFS | [SVG](assets/search_trees/missionaries_cannibals_tree.svg) · [PNG](assets/search_trees/missionaries_cannibals_tree.png) · [DOT](assets/search_trees/missionaries_cannibals_tree.dot) | complete graph-search tree: 33 of 49 nodes drawn, the 16 repeated-state leaves left out |
| Rotating Workforce Scheduling, DFS | [SVG](assets/search_trees/workforce_scheduling_tree.svg) · [PNG](assets/search_trees/workforce_scheduling_tree.png) · [DOT](assets/search_trees/workforce_scheduling_tree.dot) | partial: 64 of 82 nodes (depth ≤ 2 plus the 21-step solution path) |

Re-generate them with:

```
python main.py eight-puzzle --strategy dfs --tree-depth 5 --tree-nodes 40 --graph docs/assets/search_trees/eight_puzzle_dfs_tree
python main.py eight-puzzle --tree-depth 2 --tree-nodes 20 --graph docs/assets/search_trees/eight_puzzle_tree
python main.py missionaries --explore-all --tree-depth 11 --tree-nodes 60 --graph docs/assets/search_trees/missionaries_cannibals_tree
python main.py workforce --tree-depth 2 --tree-nodes 20 --graph docs/assets/search_trees/workforce_scheduling_tree
```

The statistics printed with every run always describe the whole tree that was
built, not only the drawn part.

Checks: `tests/test_search_tree_graphics.py` verifies, for all four
diagrams, that the root is the initial state at the top (expansion number 1),
the goal node is marked and the complete solution path is drawn, every drawn
edge is a real parent-child transition with the correct action label, every
node shows the state and expansion order of the real search node, drawn +
omitted + hidden-duplicate nodes add up to the tree size, no two nodes
overlap, the problem-specific styles (blue blank, `[m, c, b]` / `[x y d]`
notation, schedule grids with rule captions), the SVG is valid XML with one
edge element per transition, and the DOT and PNG exports and the CLI option
work. An SVG produced by this code was also rendered in a browser to
confirm that it displays correctly.

## 4. Running

```
python main.py eight-puzzle [--initial "..."] [--goal "..."]
python main.py missionaries [-m 3] [-c 3] [-b 2]
python main.py workforce [--config file.json]
```

Common options: `--strategy {bfs,dfs}`, `--max-depth`, `--max-nodes`,
`--time-limit`, `--no-duplicate-detection`, `--explore-all`, `--tree-depth`,
`--tree-nodes`, `--no-solution-path`, `--graph STEM`, `--mermaid FILE`. Exit codes: 0 solved and validated,
1 no solution / limit reached / validation failed, 2 invalid input.

## 5. Tests

`tests/test_search_tree_core.py` checks the engine on a small graph with a
cycle, an invalid transition and two goals: BFS shortest path and level
order, DFS order, parent-child links, duplicate and invalid leaves, depth
limit, tree search without duplicate detection, node and time limits, a goal
at the root, invalid parameters, statistic identities, and both renderers.
The results of all Phase 4 test files are in Section 14 of each problem
document.
