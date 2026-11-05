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

## 3. Visualization — [`search_trees/visualization.py`](../search_trees/visualization.py)

Search trees grow exponentially, so they are never drawn in full:

* **Text tree** (always printed): indented, one line per node:
  `[id] d=depth action -> state (status; reason)`. The view is limited by
  `--tree-depth` (default 3) and `--tree-nodes` (default 40); nodes on the
  solution path are always included. The last line says whether the view is
  complete or partial and how many nodes are hidden.
* **Mermaid diagram** (`--mermaid FILE`): a `flowchart TD` with the same
  depth/node limits, edge labels = actions, and colour classes: start (blue),
  goal (green), solution path (green border), duplicate (grey, dashed),
  invalid (red), not expanded / depth limit (yellow). A note node states
  "Partial tree: k of N nodes shown" whenever the drawing is partial.

**A depth-limited drawing is a partial representation of the complete search
tree.** The statistics printed below the drawing always describe the whole
tree that was built.

The Mermaid output was checked by parsing and rendering diagrams of all three
problems with Mermaid 10.9.1. The diagrams in the per-problem documents were
generated by the CLI.

## 4. Running

```
python main.py eight-puzzle [--initial "..."] [--goal "..."]
python main.py missionaries [-m 3] [-c 3] [-b 2]
python main.py workforce [--config file.json]
```

Common options: `--strategy {bfs,dfs}`, `--max-depth`, `--max-nodes`,
`--time-limit`, `--no-duplicate-detection`, `--explore-all`, `--tree-depth`,
`--tree-nodes`, `--mermaid FILE`. Exit codes: 0 solved and validated,
1 no solution / limit reached / validation failed, 2 invalid input.

## 5. Tests

`tests/test_search_tree_core.py` checks the engine on a small graph with a
cycle, an invalid transition and two goals: BFS shortest path and level
order, DFS order, parent-child links, duplicate and invalid leaves, depth
limit, tree search without duplicate detection, node and time limits, a goal
at the root, invalid parameters, statistic identities, and both renderers.
The results of all Phase 4 test files are in Section 14 of each problem
document.
