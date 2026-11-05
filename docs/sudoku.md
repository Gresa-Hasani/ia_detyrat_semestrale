# Problem 2 — Sudoku Solver (Breadth First Search with Backtracking)

Numbers labelled **measured** were produced by running the implementation in
this repository (Python 3.13.1, Windows 11). Numbers labelled **theoretical**
are computed from the puzzle alone by
[`sudoku/landscape.py`](../sudoku/landscape.py). Elapsed times and memory
depend on the machine; all other measured values are deterministic.

---

## 1. Problem Description

Write a program that solves a 9×9 Sudoku and supports three difficulty levels:
Easy, Medium and Hard. A Sudoku is a 9×9 grid divided into nine 3×3 boxes;
some cells contain given digits (clues). The task is to fill every empty cell
with a digit 1–9 so that every row, every column and every box contains each
digit exactly once.

## 2. Mathematical Model

Index the cells by `i = 9r + c` with `r, c ∈ {0,…,8}`. Let `R_r`, `C_c`, `B_b`
be the sets of cells of row `r`, column `c` and box `b`; together they form
the set `U` of 27 **units**. Let `G` be the set of clue cells with given
values `g_i`.

Find `x = (x_0, …, x_80)` with

```
x_i ∈ {1, …, 9}                      for all i
x_i = g_i                            for all i ∈ G          (clues fixed)
AllDifferent(x_j : j ∈ u)            for all u ∈ U          (27 units)
```

Because each unit has 9 cells and 9 possible digits, `AllDifferent` on a
complete unit is equivalent to "each digit 1–9 appears exactly once".

This is a **Constraint Satisfaction Problem (CSP)** with 81 variables,
finite domains and 27 global `AllDifferent` constraints (equivalently,
810 binary `≠` constraints between the 20 **peers** of each cell).

## 3. Problem Representation

* **Grid:** a tuple of 81 integers, `0` = empty
  ([`model.py`](../sudoku/model.py)). Input accepts 81 characters with `.` or
  `0` for empty cells; whitespace and `|`, `-`, `+` are ignored, so a drawn
  grid is accepted too.
* **Search state** ([`solver.py`](../sudoku/solver.py), `SearchNode`): the grid,
  three tuples of 9 bitmasks (digits used in every row, column, box), the
  number of empty cells, the depth, and a parent link with the assignment
  `(cell, digit)` that produced it.
* The legal digits of a cell are
  `ALL_DIGITS & ~(rows[r] | cols[c] | boxes[b])`, computed in O(1).

## 4. Variables and Domains

| Element | Definition |
|---|---|
| Variables | `X_0 … X_80`, one per cell |
| Domains | `D(X_i) = {g_i}` for clue cells, `{1,…,9}` for empty cells |
| Current domain during search | digits not yet used in the cell's row, column and box |

## 5. Initial State

The puzzle grid, after validation:

1. exactly 81 cells, every value in 0–9 (otherwise `SudokuError`);
2. no digit repeated in any row, column or box among the clues (otherwise
   `SudokuError` naming the digit, the unit and both cells, e.g.
   `digit 5 repeated in row 1 (r1c1 and r1c2)`);
3. forward check of the root: every empty cell must have at least one legal
   digit; if not, the result is `no_solution` without any expansion.

## 6. Goal State

A grid with no empty cells and no constraint violations that keeps every clue.
The goal test is applied when a state is generated: since every generated
state is consistent, a generated state with 0 empty cells is a solution.

## 7. Constraints

| Id | Constraint | Where enforced |
|---|---|---|
| S1 | Each row contains 1–9 exactly once | solver: row bitmask; validator: `set(row) == {1..9}` |
| S2 | Each column contains 1–9 exactly once | solver: column bitmask; validator: column set |
| S3 | Each 3×3 box contains 1–9 exactly once | solver: box bitmask; validator: box set |
| S4 | Clues cannot be modified | solver: only empty cells are ever selected; validator: compares with the puzzle |
| S5 | Every completed solution satisfies S1–S4 | the independent validator re-checks every solution |

## 8. Objective Function

[`objective.py`](../sudoku/objective.py) evaluates any grid `x`, complete or
partial:

```
V(x)   = Σ_{u ∈ U} Σ_{d=1..9} max(0, n_{u,d}(x) − 1)     (constraint violations)
E(x)   = |{ i : x_i empty }|                              (missing values)
Φ(x)   = V(x) + E(x)                                      (minimise)
```

`n_{u,d}(x)` is how many times digit `d` appears in unit `u`.

* **Partial states:** a partial grid is *consistent* when `V(x) = 0`. BFS only
  keeps consistent states, so for every state in the queue `Φ(x) = E(x)`,
  the number of cells still to fill. `Φ` decreases by exactly 1 per level.
* **Counting violations:** every extra copy of a digit inside a unit counts as
  one violation. Two 5s in the same row and box give `V = 2` (one for the
  row, one for the box); three 7s in one column and box give `V = 4`.
* **Complete valid solution:** `Φ(x) = 0`, i.e. `E(x) = 0` and `V(x) = 0`.

## 9. Landscape Calculation

### 9.1 Theoretical landscape

| Quantity | Formula |
|---|---|
| Search depth | `E` = number of empty cells |
| Naive bound | `9^E` (every empty cell any digit) |
| Initial domain product | `Π_{i empty} |D_0(X_i)|`, where `D_0` are the legal digits given the clues — a tighter upper bound on complete assignments consistent with the clues pairwise |
| Total initial candidates | `Σ_{i empty} |D_0(X_i)|` |
| Valid complete Sudoku grids | 6,670,903,752,021,072,936,960 ≈ 6.67×10²¹ (Felgenhauer and Jarvis, 2005; literature constant, not computed here) |
| Maximum branching factor | 9 digits per expanded state (the formulation tries every digit) |

**Theoretical** values per puzzle:

| Puzzle | Clues | E (depth) | 9^E | Initial domain product | Total candidates | Average domain size | Singleton cells |
|---|---|---|---|---|---|---|---|
| Easy | 30 | 51 | 4.638e+48 | 4.259e+22 | 153 | 3.000 | 4 |
| Medium | 27 | 54 | 3.381e+51 | 3.019e+27 | 190 | 3.519 | 3 |
| Hard | 21 | 60 | 1.797e+57 | 9.586e+36 | 254 | 4.233 | 0 |
| extra-17-clues | 17 | 64 | 1.179e+61 | 1.741e+42 | 301 | 4.703 | 0 |
| extra-36-clues | 36 | 45 | 8.727e+42 | 139,314,069,504 | 87 | 1.933 | 15 |

Large values are shown as a truncated mantissa × power of ten.

### 9.2 Measured landscape

Limits: 1,000,000 expanded states, 2,000,000 queued states, 120 s. Peak
memory was measured with `tracemalloc` (it slows the run, so times in this
table are higher than in normal runs).

| Puzzle | Order | Status | Expanded | Generated | Tested | Invalid partial states | Dead ends = backtracks | Failed expansions | Duplicates | Max queue | Widest level (states @ depth) | cBF | eBF | Peak memory | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Easy | MRV | solved | 51 | 51 | 451 | 400 | 0 | 0 | 0 | 1 | 1 @ every depth | 1.000 | 1.000 | 0.1 MiB | 0.02 s |
| Easy | row-major | solved | 335 | 335 | 3,007 | 2,480 | 192 | 69 | 0 | 32 | 32 @ 7 | 1.573 | 1.000 | 0.3 MiB | 0.06 s |
| Medium | MRV | solved | 100 | 100 | 894 | 791 | 3 | 3 | 0 | 4 | 4 @ 22 | 1.030 | 1.000 | 0.1 MiB | 0.02 s |
| Medium | row-major | solved | 4,522 | 4,522 | 40,692 | 34,008 | 2,162 | 790 | 0 | 672 | 672 @ 22 | 1.478 | 1.000 | 3.7 MiB | 1.07 s |
| Hard | MRV | solved | 17,136 | 17,136 | 154,217 | 135,282 | 1,799 | 1,799 | 0 | 826 | 826 @ 27 | 1.105 | 1.000 | 13.6 MiB | 5.58 s |
| Hard | row-major | solved | 517,786 | 517,786 | 4,660,067 | 3,860,946 | 281,335 | 132,705 | 0 | 61,667 | 61,667 @ 30 | 1.543 | 1.000 | 426.4 MiB | 119.74 s |
| extra-17-clues | MRV | solved | 2,356 | 2,356 | 21,198 | 18,505 | 337 | 337 | 0 | 128 | 122 @ 18 | 1.143 | 1.000 | 1.8 MiB | 0.71 s |
| extra-17-clues | row-major | limit (time) | 436,736 | 617,829 | 3,930,624 | 3,282,121 | 30,674 | 3,191 | 0 | 181,094 | 134,072 @ 21 | 1.485 | 1.415 | 722.7 MiB | 120.03 s |
| extra-36-clues | MRV | solved | 45 | 45 | 405 | 360 | 0 | 0 | 0 | 1 | 1 @ every depth | 1.000 | 1.000 | 0.0 MiB | 0.04 s |
| extra-36-clues | row-major | solved | 45 | 45 | 405 | 351 | 9 | 0 | 0 | 1 | 1 @ every depth | 1.200 | 1.000 | 0.0 MiB | 0.01 s |

Without `tracemalloc`, using the CLI's default limits (1,000,000 states, 60 s):
Hard with row-major ordering is solved in 24.1 s (517,786 states, max queue
61,667); extra-17-clues with row-major ordering stops at the 1,000,000-state
limit after 32.5 s with **1,028,729 states in the queue** and no solution.

All solutions in the table passed the independent validator, and
`--count-solutions` confirms that every puzzle above has exactly one solution.
With MRV, Easy and extra-36-clues are classified as **easy**, Medium as
**medium**, and Hard and extra-17-clues as **hard**.

Definitions:

* **expanded** — states removed from the front of the queue and expanded;
* **generated** — consistent, non-dead-end children appended to the queue
  (including goal states);
* **tested** — `(state, digit)` pairs tried, always `9 × expanded`;
* **invalid partial states** — digits rejected because they already appear in
  the row, column or box (they would give `V > 0`);
* **dead ends = backtracks** — consistent children discarded by the forward
  check because some empty peer would have no legal digit;
* **failed expansions** — expanded states none of whose children survived
  (a whole branch abandoned);
* **max queue** — the largest number of states stored in the FIFO queue at
  once; **widest level** — the BFS level with the most generated states;
* **cBF** (consistent branching factor) — non-conflicting digits per expanded
  state; **eBF** (effective) — children kept per expanded state.

### 9.3 How the landscape changes across difficulty levels

* Easy has many **singleton cells** (cells with only one legal digit) from the
  start. With MRV every expansion has exactly one legal child: the search tree
  is a single path, the queue never holds more than one state and no
  backtracking happens.
* Medium has few singletons; BFS must branch a few times, the queue grows to a
  handful of states and a few dead ends appear.
* Hard has **no** singleton cells and the largest average domain. The BFS
  frontier grows to hundreds of states in the middle levels and thousands of
  dead ends must be pruned.
* **Clue count alone is not the difficulty.** The 17-clue extra puzzle needs
  far fewer states than the 21-clue Hard puzzle, and the 36-clue extra puzzle
  is as easy as Easy. That is why the difficulty classification uses measured
  search effort.
* With row-major ordering the frontier is much wider: BFS has to keep every
  consistent partial grid of a level. The Hard puzzle needs 517,786 states, a
  queue of 61,667 states and about 426 MiB; the 17-clue extra puzzle exceeds
  the limits with more than a million queued states.

## 10. Algorithm Used — Breadth First Search with Backtracking

### Why BFS here

The assignment requires BFS. For Sudoku every solution lies at the same depth
`E`, so BFS is complete (it finds a solution whenever one exists, within
limits) and, as a side effect, it finds **all** solutions on the same last
level — useful to check uniqueness (`--count-solutions`).

### How BFS and backtracking work together

* **BFS:** the frontier is a FIFO queue (`collections.deque`). States are taken
  from the front (`popleft`) and children are added at the back (`append`), so
  all states with `d` filled cells are expanded before any state with `d+1`
  filled cells. `test_bfs_expands_states_in_fifo_level_order` records the
  depth of every expanded state and checks that the sequence never
  decreases and that each level is fully expanded before the next.
* **Variable selection:** each state fills exactly one cell. By default this is
  the cell with the fewest legal digits (MRV, "minimum remaining values", ties
  broken by the lowest index); `--order row-major` uses the first empty cell
  instead. Either way the choice is a deterministic function of the state, so
  the search tree is well defined.
* **Backtracking:** BFS keeps all alternatives of a level in the queue instead
  of on a recursion stack. Every partial assignment is checked the moment it
  is created:
  1. a digit already used in the cell's row, column or box is rejected
     (invalid partial state);
  2. **forward check:** if the new digit leaves an empty peer with no legal
     digit, the child is a dead end and is discarded.

  Discarding a dead end abandons that partial assignment, and the search
  resumes with the next alternative waiting in the queue. This is the
  backtracking step. When an expanded state has no surviving child, its whole
  branch is abandoned.
* **Path reconstruction:** each state keeps a parent link and its assignment;
  the solution path is traced back from the goal to the root
  (`--show-path`).
* **Duplicate detection:** a `visited` set of grids prevents enqueuing a grid
  twice. Because the cell choice is deterministic, every partial grid has a
  unique path from the root, so the measured number of duplicates is always 0;
  the set is kept as a safety net and its cost is part of the memory figures.

### A property of MRV that the measurements show

With MRV, a dead end can only appear when the selected cell has exactly one
legal digit. If any empty cell has one legal digit, MRV selects such a cell;
otherwise every empty cell has at least two, and one assignment removes at
most one digit from each peer, so no peer can drop to zero. Each pruned child
is therefore the only child of its parent, which is why
`dead ends = failed expansions` in every MRV row
(`test_mrv_dead_ends_only_at_forced_cells`).

## 11. Pseudocode

```
function BFS_SOLVE(puzzle, order, limits):
    VALIDATE(puzzle)                                   // 81 cells, no conflicting clues
    root ← STATE(puzzle)
    if some empty cell of root has no legal digit: return NO_SOLUTION
    if root is complete:                         return root
    queue ← FIFO[root];  visited ← {root.grid}
    while queue not empty:
        CHECK_LIMITS(queue)
        s ← queue.POP_FRONT()                          // oldest state first
        cell ← SELECT_CELL(s, order)                   // MRV or row-major
        kept ← 0
        for digit in 1..9:
            if digit ∈ used(row, col, box of cell):    // invalid partial state
                continue
            child ← s with cell := digit
            if some empty peer of cell has no legal digit in child:
                continue                               // dead end → backtrack
            if child.grid ∈ visited: continue
            visited.ADD(child.grid);  kept ← kept + 1
            if child has no empty cell:                // goal test on generation
                record solution; if not count_all: return child
            else:
                queue.PUSH_BACK(child)
        if kept = 0: failed_expansions ← failed_expansions + 1
    return solutions found, or NO_SOLUTION
```

## 12. Implementation Explanation

| File | Responsibility |
|---|---|
| [`model.py`](../sudoku/model.py) | grid parsing, the 27 units, conflict detection, initial validation, text rendering |
| [`solver.py`](../sudoku/solver.py) | `SudokuBFS` (FIFO BFS), `SearchNode`, `SearchLimits`, `SearchStats`, `SearchResult` |
| [`validator.py`](../sudoku/validator.py) | independent validator (plain sets, own index arithmetic, no shared code with the solver) |
| [`objective.py`](../sudoku/objective.py) | `V(x)`, `E(x)`, `Φ(x)` |
| [`landscape.py`](../sudoku/landscape.py) | theoretical landscape |
| [`puzzles.py`](../sudoku/puzzles.py) | Easy/Medium/Hard puzzles and the measured difficulty classification |
| [`report.py`](../sudoku/report.py), [`cli.py`](../sudoku/cli.py) | output and command-line interface |

### Difficulty classification

Difficulty is assigned from the statistics of an actual MRV-BFS run
(`classify_difficulty`):

| Level | Rule (measured) |
|---|---|
| Easy | no backtracking and max queue size 1 — every expansion is forced |
| Medium | backtracking needed, at most 1,000 expanded states |
| Hard | more than 1,000 expanded states |

The predefined puzzles:

| Level | Clues | Source |
|---|---|---|
| Easy | 30 | example puzzle of the Wikipedia "Sudoku" article |
| Medium | 27 | — |
| Hard | 21 | Arto Inkala's puzzle published in 2012 as "the world's hardest Sudoku" |

The tests re-run the solver and assert that each predefined puzzle falls into
its declared level, that each has exactly one solution, and that the search
effort strictly increases from Easy to Medium to Hard.

### Limits and failure results

`SearchLimits` bounds expanded states (`--max-states`), queue size
(`--max-queue`) and time (`--time-limit`). The result status is one of
`solved`, `no_solution` (search space exhausted) or `limit_reached`
(inconclusive). The CLI exits with 0 when solved and validated, 1 when no
solution was found or validation failed, and 2 for invalid input.

## 13. Complexity Analysis

Let `E` be the number of empty cells and `b ≤ 9` the branching factor.

* **Time:** `O(b^E)` states in the worst case (bounded by the initial domain
  product). Each expansion costs `O(81)` for MRV selection plus `O(9 · 20)`
  for the conflict and forward checks; creating a child copies 81 cells.
  Generalised `n²×n²` Sudoku is NP-complete (Yato and Seta, 2003), so no
  polynomial algorithm is expected.
* **Space:** BFS must keep a whole level in memory: `O(b^d)` states at depth
  `d`, each `O(81)`. This is the main practical limitation of BFS compared with
  DFS, whose memory is `O(E)`. The `visited` set and parent links add
  memory proportional to the number of generated states.
* **Measured:** with MRV the widest level is small (1 / 4 / 826 states for
  Easy / Medium / Hard). With row-major ordering the Hard puzzle's widest level
  holds 61,667 states (about 426 MiB peak), and the 17-clue extra puzzle passes
  1,000,000 queued states without finding the solution. This shows the
  exponential memory growth of BFS directly.

## 14. Test Results

Command: `python -m pytest -v tests/test_sudoku.py`.

Measured result: **62 tests collected, 62 passed, 0 failed, 6.7 s**
(Python 3.13.1, pytest 9.0.2). The complete project suite
(`python -m pytest`) runs **130 tests, 130 passed** (68 Social Golfers + 62 Sudoku).

| Test class | Tests | What is verified |
|---|---|---|
| `TestParsingAndInitialValidation` | 14 | 81-cell parsing, drawn grids, bad characters/lengths, conflicting clues in row/column/box, bad grids, invalid order and limits |
| `TestValidator` | 7 | valid solution, changed clue, broken rows, malformed solutions |
| `TestObjective` | 3 | `Φ = 0` for a solution, `Φ = E` for the puzzle, violation counting |
| `TestLandscape` | 4 | bounds for the Easy, complete, empty and 2-solution grids |
| `TestBFSSolver` | 26 | all three levels solved and validated, measured difficulty matches the label, uniqueness of all puzzles, effort grows Easy < Medium < Hard, **FIFO level order**, 2-solution puzzle, unsolvable at the root and after 3,851 states, already-solved grid, solution path, MRV vs row-major, statistic identities, the MRV dead-end property, state/queue/time limits |
| `TestCLI` | 8 | the three levels, puzzle file with path output, invalid puzzle, missing file, unsolvable puzzle, solution counting |

## 15. Execution Examples

```
python main.py sudoku -d hard
```

```
Sudoku (hard) - Breadth First Search with backtracking

8 . . | . . . | . . .
. . 3 | 6 . . | . . .
. 7 . | . 9 . | 2 . .
------+-------+------
. 5 . | . . 7 | . . .
. . . | . 4 5 | 7 . .
. . . | 1 . . | . 3 .
------+-------+------
. . 1 | . . . | . 6 8
. . 8 | 5 . . | . 1 .
. 9 . | . . . | 4 . .

Theoretical landscape:
  Clues                             : 21
  Empty cells E (search depth)      : 60
  Naive bound 9^E                   : 1.797e+57
  Initial domain product            : 9.586e+36
  ...
Measured search statistics:
  Status                            : solved
  States expanded (dequeued)        : 17,136
  Backtracks                        : 1,799
  Max queue size                    : 826
  Widest BFS level                  : 826 states at depth 27
  Measured difficulty               : hard
  Independent validation            : PASSED

Solution:
8 1 2 | 7 5 3 | 6 4 9
9 4 3 | 6 8 2 | 1 7 5
6 7 5 | 4 9 1 | 2 8 3
------+-------+------
1 5 4 | 2 3 7 | 8 9 6
3 6 9 | 8 4 5 | 7 2 1
2 8 7 | 1 6 9 | 5 3 4
------+-------+------
5 2 1 | 9 7 4 | 3 6 8
4 3 8 | 5 2 6 | 9 1 7
7 9 6 | 3 1 8 | 4 5 2
```

Other commands:

```
python main.py sudoku -d easy
python main.py sudoku -d medium --show-path        # print the 54 assignments
python main.py sudoku -d hard --order row-major    # much wider frontier (517,786 states)
python main.py sudoku --puzzle "534..8912672195348198342567859..1423426853791713924856961537284287419635345286179" --count-solutions   # 2 solutions
python main.py sudoku --file my_puzzle.txt
python main.py sudoku --puzzle "55..."             # error: invalid puzzle
```

## 16. Implementation Limitations

* **Memory:** BFS stores whole levels. With MRV the predefined puzzles need
  little memory, but a poor variable order (row-major) or a puzzle with very
  many solutions (e.g. an almost empty grid) makes the frontier grow
  exponentially until `--max-queue` or `--max-states` stops the search.
* **First-solution mode saves little:** all solutions sit on the last level,
  so BFS reaches the first one only after expanding almost the whole tree.
* **Only basic constraint checking:** the solver uses conflict checks and a
  peer forward check; it does not use stronger propagation (naked/hidden
  singles applied repeatedly, arc consistency), which would shrink the search
  further but would no longer be a plain BFS over single assignments.
* **9×9 only:** the code is written for the standard 9×9 grid.
* **Difficulty thresholds** (0 backtracks / 1,000 states) are a documented
  project rule applied to MRV-BFS statistics; other solvers would give
  different numbers.
