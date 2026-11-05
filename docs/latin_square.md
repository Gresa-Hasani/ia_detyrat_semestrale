# Problem 3 — Latin Square (Iterative Deepening DFS with Backtracking)

Numbers labelled **measured** were produced by running the implementation in
this repository (Python 3.13.1, Windows 11). Numbers labelled **theoretical**
come from formulas in [`latin_square/landscape.py`](../latin_square/landscape.py);
counts quoted from the literature are marked as such. Times depend on the
machine; all other measured values are deterministic.

---

## 1. Problem Description

A Latin square of order `n` is an `n × n` grid filled with `n` different
values, each appearing exactly once in every row and every column. Given `n`,
print an `n × n` matrix of the numbers 1..n with this property.

Example from the assignment (`n = 5`), confirmed valid by the validator
(`test_assignment_example_is_valid`):

```
1 2 3 4 5
5 1 2 3 4
4 5 1 2 3
3 4 5 1 2
2 3 4 5 1
```

## 2. Mathematical Model

Find `x = (x_{r,c})`, `0 ≤ r, c < n`, with

```
x_{r,c} ∈ {1, …, n}                                 for all r, c
x_{r,c} ≠ x_{r,c'}                                  for all r and c ≠ c'   (rows)
x_{r,c} ≠ x_{r',c}                                  for all c and r ≠ r'   (columns)
```

Equivalently, `AllDifferent` on each of the `n` rows and `n` columns. A row of
`n` cells with `n` distinct values from `{1..n}` contains every value exactly
once, so this matches the definition.

It is a **Constraint Satisfaction Problem (CSP)**. A solution always exists
for every `n ≥ 1` (for example the cyclic square `x_{r,c} = ((c − r) mod n) + 1`,
which is the assignment's example), so the interesting part is *how much
search* IDDFS needs to construct one.

## 3. Problem Representation

* **Grid:** a tuple of `n` rows of `n` integers, `0` = empty
  ([`model.py`](../latin_square/model.py)).
* **Search state:** a consistent partial grid in which the first `d` free
  cells (row-major order) are filled; `d` is the depth. The solver keeps one
  mutable grid plus a bitmask per row and per column of the values already
  used, so a constraint check is `(rows[r] | cols[c]) & (1 << v)` — O(1).
* **Symmetry breaking (default):** the *reduced form* fixes the first row and
  the first column to `1..n`. This is sound for generation: permuting the
  values turns the first row of any Latin square into `1..n`, then permuting
  rows 2..n turns the first column into `1..n`. `--no-symmetry-breaking`
  searches the full empty grid.
* **Extension (not required by the assignment):** `--prefill` starts from a
  partially filled grid (Latin square *completion*). It is used to test
  unsolvable configurations, which cannot occur for an empty grid.

## 4. Variables and Domains

| Element | Definition |
|---|---|
| Variables | `x_{r,c}`, `n²` cells (`(n−1)²` free cells in reduced form) |
| Domains | `{1, …, n}`; fixed cells have a single value |
| Current domain during search | values not yet used in the cell's row and column |

## 5. Initial State

* Full grid: all `n²` cells empty, depth 0.
* Reduced form (default): first row and column = `1..n`; `D = (n − 1)²` free cells.
* Custom pre-fill: the given grid after validation (shape, values 0..n, no
  repeated value in a row or column).

## 6. Goal State

A state in which all `D` free cells are filled. Every state on the search path
is consistent (invalid values are rejected before a node is created), so a
complete state is a valid Latin square. Goals exist only at depth `D`.

## 7. Constraints

| Id | Constraint | Where enforced |
|---|---|---|
| L1 | Grid dimensions are `n × n` | model: `check_grid`; validator: row/column counts |
| L2 | Values are in `1..n` | solver: values tried are `1..n`; validator: range check |
| L3 | No repeated value in a row | solver: row bitmask; validator: `set(row) == {1..n}` |
| L4 | No repeated value in a column | solver: column bitmask; validator: column set |
| L5 | Every cell eventually holds a valid value | goal test at depth `D`; validator rejects 0 |

## 8. Objective Function

[`objective.py`](../latin_square/objective.py):

```
V(x)   = Σ_{lines L} Σ_{v=1..n} max(0, n_{L,v}(x) − 1)     (violations; lines = rows and columns)
E(x)   = number of empty cells
Φ(x)   = V(x) + E(x)                                        (minimise)
```

* **Partial grids:** consistent when `V = 0`; IDDFS only creates consistent
  states, so along the search `Φ = E = D − depth`.
* **Complete grids:** `E = 0`, so `Φ = V`. A complete valid Latin square has
  `Φ = 0`. For example, a row holding the value 1 three times contributes 2
  violations.

## 9. Landscape Calculation

### 9.1 Theoretical landscape

| Quantity | Formula | n = 3 | n = 4 | n = 5 |
|---|---|---|---|---|
| Free cells `D` (full / reduced) | `n²` / `(n−1)²` | 9 / 4 | 16 / 9 | 25 / 16 |
| Naive assignments (full grid) | `n^(n²)` | 19,683 | 4.294e+9 | 2.980e+17 |
| Row-permutation bound | `(n!)^n` (each row a permutation) | 216 | 331,776 | 2.488e+10 |
| Unpruned tree, full grid | `Σ_{d=0..D} n^d` | 29,524 | 5.726e+9 | 3.725e+17 |
| Unpruned IDDFS work, full grid | `Σ_{L=0..D} Σ_{d=0..L} n^d` | 44,281 | 7.635e+9 | 4.656e+17 |
| Latin squares `L(n)` (literature, OEIS A002860) | — | 12 | 576 | 161,280 |
| Reduced squares `R(n)` (literature, OEIS A000315) | `L(n) = n!(n−1)! R(n)` | 1 | 4 | 56 |
| Maximum branching factor | `n` | 3 | 4 | 5 |

`L(6) = 812,851,200` and `L(7) = 61,479,419,904,000`. The literature counts
are reproduced by exhaustive search for `n ≤ 4` (full grid) and `n ≤ 6`
(reduced form) — see Section 14.

### 9.2 Measured landscape

Command used: the solver with no node limit, 300 s time limit (60 s for the
largest cases), value order 1..n, row-major cell order.

| n | Mode | Step | Status | Iterations | Nodes visited (all) | Nodes visited (last) | Repeated-work ratio | Expanded | Invalid assignments | Backtracks | Dead ends | eBF | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | reduced | 1 | solved | 1 | 1 | 1 | 1.00 | 0 | 0 | 0 | 0 | — | 0.00 s |
| 1 | full | 1 | solved | 2 | 3 | 2 | 1.50 | 1 | 0 | 0 | 0 | 1.000 | 0.00 s |
| 2 | reduced | 1 | solved | 2 | 3 | 2 | 1.50 | 1 | 0 | 0 | 0 | 1.000 | 0.00 s |
| 2 | full | 1 | solved | 5 | 21 | 5 | 4.20 | 13 | 8 | 12 | 0 | 1.231 | 0.00 s |
| 3 | reduced | 1 | solved | 5 | 19 | 6 | 3.17 | 13 | 20 | 10 | 3 | 1.077 | 0.00 s |
| 3 | full | 1 | solved | 10 | 326 | 11 | 29.64 | 243 | 404 | 307 | 19 | 1.300 | 0.00 s |
| 4 | reduced | 1 | solved | 10 | 161 | 10 | 16.10 | 126 | 338 | 142 | 15 | 1.198 | 0.00 s |
| 4 | full | 1 | solved | 17 | 24,861 | 17 | 1,462.41 | 19,755 | 54,152 | 24,828 | 1,776 | 1.258 | 0.13 s |
| 5 | reduced | 1 | solved | 17 | 4,914 | 29 | 169.45 | 4,120 | 15,669 | 4,881 | 690 | 1.189 | 0.02 s |
| 5 | full | 1 | solved | 26 | 13,505,923 | 38 | 355,419.03 | 11,353,036 | 43,259,233 | 13,505,872 | 1,717,327 | 1.190 | 114.79 s |
| 6 | reduced | 1 | solved | 26 | 1,194,077 | 52 | 22,963.02 | 1,030,569 | 4,989,298 | 1,194,026 | 185,684 | 1.159 | 10.24 s |
| 6 | full | 1 | time limit (60 s) | 16 | 9,984,000 | 3,287,871 | — | 3,894,585 | 13,383,486 | 9,983,970 | 104,387 | 2.564 | 60.01 s |
| 7 | reduced | 1 | time limit (60 s) | 18 | 8,628,224 | 2,389,741 | — | 4,303,095 | 21,493,416 | 8,628,192 | 205,178 | 2.005 | 60.00 s |
| 7 | full | 1 | time limit (60 s) | 13 | 11,520,000 | 7,153,801 | — | 3,613,314 | 13,773,172 | 11,519,976 | 0 | 3.188 | 60.00 s |
| 4 | full | 4 | solved | 5 | 4,245 | 17 | 249.71 | 3,427 | 9,444 | 4,224 | 432 | 1.237 | 0.02 s |
| 4 | reduced | 3 | solved | 4 | 48 | 10 | 4.80 | 39 | 97 | 35 | 5 | 1.128 | 0.00 s |
| 5 | full | 5 | solved | 6 | 1,842,863 | 38 | 48,496.39 | 1,609,941 | 6,206,798 | 1,842,832 | 326,287 | 1.145 | 10.00 s |
| 5 | reduced | 4 | solved | 5 | 941 | 29 | 32.45 | 826 | 3,160 | 920 | 174 | 1.133 | 0.01 s |
| 6 | full | 6 | time limit (60 s) | 4 | 11,378,688 | 10,761,333 | — | 8,566,598 | 40,020,862 | 11,378,668 | 1,195,660 | 1.328 | 60.00 s |
| 6 | reduced | 5 | solved | 6 | 173,456 | 52 | 3,335.69 | 156,377 | 764,747 | 173,425 | 35,250 | 1.109 | 0.96 s |

* **Nodes visited** — states reached (calls of the depth-limited search);
* **repeated-work ratio** — nodes of all iterations / nodes of the final
  iteration (how much more IDDFS did than one DFS with the right limit);
* **invalid assignments** — values rejected because they already appear in
  the row or column; **valid assignments** = nodes visited − 1 per iteration;
* **backtracks** — assignments undone; **dead ends** — expanded states in which
  no value fits; **eBF** — valid assignments per expanded state.

### 9.3 Nodes explored per depth limit (measured)

Full grid, `n = 5`. **Cutoffs** are the states that sit exactly at the depth
limit: they are not expanded, and their number equals the number of **valid
partial states** with `L` cells filled.

| Limit L | Nodes visited | Cutoffs (valid states at depth L) | | Limit L | Nodes visited | Cutoffs |
|---|---|---|---|---|---|---|
| 0 | 1 | 1 | | 13 | 149,846 | 76,560 |
| 1 | 6 | 5 | | 14 | 250,646 | 100,800 |
| 2 | 26 | 20 | | 15 | 316,886 | 66,240 |
| 3 | 86 | 60 | | 16 | 449,366 | 132,480 |
| 4 | 206 | 120 | | 17 | 681,206 | 231,840 |
| 5 | 326 | 120 | | 18 | 1,012,406 | 331,200 |
| 6 | 806 | 480 | | 19 | 1,346,486 | 334,080 |
| 7 | 2,366 | 1,560 | | 20 | 1,507,766 | 161,280 |
| 8 | 6,206 | 3,840 | | 21 | 1,669,046 | 161,280 |
| 9 | 12,566 | 6,360 | | 22 | 1,830,326 | 161,280 |
| 10 | 17,846 | 5,280 | | 23 | 1,991,606 | 161,280 |
| 11 | 33,686 | 15,840 | | 24 | 2,152,886 | 161,280 |
| 12 | 73,286 | 39,600 | | **25** | **38** | **found** |

These measured values agree with known combinatorics, which is an
independent check of the search:

* depth 5 (one full row): `5! = 120` valid states;
* depth 10 (two rows): `5! · 44 = 5,280`, where 44 is the number of
  derangements of 5 elements (2 × 5 Latin rectangles);
* depth ≥ 20: exactly `L(5) = 161,280`. Once 4 rows are placed, the last row
  is forced, so every valid 4-row prefix extends to exactly one Latin square.

The same table for the reduced form `n = 6` ends with `9,408 = R(6)` valid
states from depth 20 on, then finds the goal at limit 25 with 52 nodes.

### 9.4 Theoretical versus explored search space

For the full `n = 5` grid the unpruned tree has `3.7 × 10^17` nodes, but
IDDFS visits 1.35 × 10^7 nodes in total, and the final iteration only 38.
Early rejection of invalid values removes almost the entire theoretical space;
what remains expensive is the *repetition* of the shallower levels in every
iteration.

## 10. Algorithm Used — Iterative Deepening DFS with Backtracking

IDDFS combines the low memory of DFS (`O(depth)`) with the completeness and
shallowest-goal property of BFS: it runs depth-limited DFS with limits
0, 1, 2, … until a goal is found.

**Why it fits, and where it does not.** IDDFS is designed for problems where
the goal depth is unknown and goals may be shallow. In a Latin square every
goal is at the maximum depth `D`, which is known in advance. So all
iterations with `L < D` are guaranteed to fail, and each of them explores
*every* valid partial state up to depth `L`. The measured repeated-work ratio
(355,419 for the full `n = 5` grid) shows this cost directly. The usual
argument that IDDFS costs only `b/(b−1)` times a single DFS assumes a uniform
tree whose last level dominates; here the final iteration stops after a few
dozen nodes, while earlier iterations are exhaustive.

**Backtracking inside each iteration.** Values are tried in the order 1..n.
A value already in the row or column is rejected before a node is created.
After a child's subtree fails (or is cut off), the assignment is undone and
the next value is tried.

**Avoiding unnecessary repeated computation without changing IDDFS.**

1. O(1) bitmask constraint checks instead of scanning rows and columns.
2. **Early termination:** each depth-limited search reports `cutoff` if it
   stopped at the limit anywhere and `failure` if it exhausted the subtree
   without a cutoff. After a `failure`, deeper limits cannot help, so IDDFS
   stops. For the pre-fill `1 2 . / . . 3 / . . .` it stops after 2 of 7
   possible iterations (`test_unsolvable_prefill_detected_early`).
3. **Symmetry breaking (reduced form):** shrinks every iteration's tree,
   reducing `n = 5` from 13.5 million to 4,914 nodes.
4. **Optional `--step k`:** depth limits 0, k, 2k, …, D (the last limit is
   always D). With `k = n` (one row per iteration) the full `n = 5` grid needs
   1.84 million instead of 13.5 million nodes. Step 1 is the default and is
   the textbook algorithm.

Storing states between iterations (memoisation) would remove the repetition
but turn IDDFS into a memory-hungry BFS-like search, so it is not done.

## 11. Pseudocode

```
function IDDFS(n, prefill, step):
    free ← empty cells of prefill in row-major order;  D ← |free|
    for L in 0, step, 2·step, …, D:              // the last limit is always D
        outcome ← DLS(depth = 0, limit = L)
        if outcome = FOUND:   return solution
        if outcome = FAILURE: return NO_SOLUTION // nothing deeper exists
    return NO_SOLUTION

function DLS(depth, L):
    if depth = D:   return FOUND                 // complete, consistent grid
    if depth = L:   return CUTOFF                // depth limit: do not expand
    (r, c) ← free[depth];  cutoff ← false
    for v in 1..n:
        if v ∈ rows[r] or v ∈ cols[c]:  continue // invalid assignment rejected
        assign x[r][c] ← v; add v to rows[r], cols[c]
        result ← DLS(depth + 1, L)
        if result = FOUND:  return FOUND
        undo x[r][c]; remove v from rows[r], cols[c]   // backtrack
        if result = CUTOFF: cutoff ← true
    return CUTOFF if cutoff else FAILURE
```

## 12. Implementation Explanation

| File | Responsibility |
|---|---|
| [`model.py`](../latin_square/model.py) | size validation, grid parsing, conflict detection, reduced form, rendering |
| [`solver.py`](../latin_square/solver.py) | `LatinSquareIDDFS`, `IterationStats`, `SearchStats`, `SearchLimits`, `SearchResult` |
| [`validator.py`](../latin_square/validator.py) | independent validator (sets, no bitmasks, no shared code with the solver) |
| [`objective.py`](../latin_square/objective.py) | `V(x)`, `E(x)`, `Φ(x)` |
| [`landscape.py`](../latin_square/landscape.py) | theoretical formulas and literature constants |
| [`report.py`](../latin_square/report.py), [`cli.py`](../latin_square/cli.py) | per-iteration table, statistics, command line |

* Statistics are recorded **per iteration** (`IterationStats`) and summed in
  `SearchStats`; the CLI prints the "nodes explored per depth limit" table.
* `--count-solutions` keeps searching in the final iteration and counts every
  goal; this is how the literature counts are reproduced.
* Limits: `--max-nodes` (summed over iterations) and `--time-limit`. A run
  that hits a limit returns `limit_reached` and the interrupted iteration is
  marked `limit`.
* Exit codes: 0 solved and validated, 1 no solution / limit reached /
  validation failed, 2 invalid input.

## 13. Complexity Analysis

Let `D` be the number of free cells and `b ≤ n` the branching factor.

* **Time:** one depth-limited search with limit `L` visits `N(L)` nodes, the
  number of consistent partial assignments of the first `L` cells (plus their
  ancestors). IDDFS costs `Σ_{L=0..D} N(≤L)`, bounded by
  `Σ_L Σ_{d≤L} b^d = O(D · b^D)` in the worst case. Each node costs O(n) to try
  the values, O(1) per check.
* **Space:** `O(D)` for the recursion stack plus `O(n²)` for the grid and `O(n)`
  bitmasks. Memory stays tiny even when millions of nodes are visited — the
  advantage of IDDFS over BFS.
* **Growth with n (measured, reduced form):** 19, 161, 4,914 and 1,194,077
  nodes for `n` = 3, 4, 5, 6; `n = 7` does not finish in 60 s. Because the
  number of Latin squares grows faster than exponentially, so does the
  number of valid partial states the early iterations must enumerate.

## 14. Test Results

Command: `python -m pytest -v tests/test_latin_square.py`.

Measured result: **80 tests collected, 80 passed, 0 failed, 20.7 s**
(Python 3.13.1, pytest 9.0.2). Results of the complete project suite are in
[final_report.md](final_report.md).

| Test class | Tests | What is verified |
|---|---|---|
| `TestModel` | 23 | grid parsing, wrong rows/cells/tokens, value range, repeated values, invalid `n`, reduced form, invalid step, pre-fill + reduced conflict, invalid limits |
| `TestValidator` | 8 | the assignment's example, repeated values in rows/columns, malformed squares, changed pre-filled cells |
| `TestObjective` | 3 | `Φ = 0` for a square, `Φ = E` for partial grids, violation counting |
| `TestLandscape` | 3 | all formulas, reduced depth, `L(n) = n!(n−1)! R(n)` for the literature constants |
| `TestIDDFS` | 34 | valid squares for n = 1..6 (reduced) and n = 1..4 (full), n = 5 full with step 5, limits start at 0 and grow by 1, every iteration stays within its limit, iterations restart from the root, **exhaustive counts equal L(n) for n ≤ 4 and R(n) for n ≤ 5**, early stop on unsolvable pre-fills, completion, statistic identities, node and time limits |
| `TestCLI` | 9 | n = 3, 4, 5, full-grid option, counting, unsolvable pre-fill, invalid inputs |

Exhaustive counts measured with `--count-solutions` (benchmark run):

| n | Full grid: squares found | Literature `L(n)` | Reduced: squares found | Literature `R(n)` |
|---|---|---|---|---|
| 1 | 1 | 1 | 1 | 1 |
| 2 | 2 | 2 | 1 | 1 |
| 3 | 12 | 12 | 1 | 1 |
| 4 | 576 | 576 | 4 | 4 |
| 5 | — | 161,280 | 56 | 56 |
| 6 | — | 812,851,200 | 9,408 (10.4 s) | 9,408 |

## 15. Execution Examples

```
python main.py latin -n 5
```

```
Latin Square n=5 (reduced form) - IDDFS with backtracking, step 1

Initial state:
1 2 3 4 5
2 . . . .
3 . . . .
4 . . . .
5 . . . .

Theoretical landscape:
  Order n / cells n^2               : 5 / 25
  Free cells D (search depth)       : 16
  Naive assignments n^D             : 152,587,890,625
  ...

Nodes explored per depth limit:
  limit     visited    expanded    rejected  backtracks    cutoffs max depth  outcome
      0           1           0           0           0          1         0  cutoff
      1           5           1           1           4          4         1  cutoff
    ...
     15         793         737       2,893         792         56        15  cutoff
     16          29          28          78          12          0        16  found

Measured search statistics:
  Status                         : solved
  IDDFS iterations               : 17
  Nodes visited (all iterations) : 4,914
  Nodes visited (last iteration) : 29
  Repeated-work ratio            : 169.45
  Backtracks                     : 4,881
  Independent validation         : PASSED

Latin square:
1 2 3 4 5
2 1 4 5 3
3 4 5 1 2
4 5 2 3 1
5 3 1 2 4
```

The result is the lexicographically first reduced Latin square in the search
order (values 1..n, row-major cells); it differs from the assignment's cyclic
example, which is another valid Latin square.

Other commands:

```
python main.py latin -n 3
python main.py latin -n 4 --no-symmetry-breaking          # full grid, 24,861 nodes
python main.py latin -n 5 --no-symmetry-breaking --step 5  # one row per iteration
python main.py latin -n 5 --count-solutions               # 56 reduced squares
python main.py latin -n 3 --prefill ". . 1/. 1 ./1 . ."   # completion (extension)
python main.py latin -n 2 --prefill "1 ./. 2"             # no completion exists
```

## 16. Implementation Limitations

* **Goals only at maximum depth.** All iterations before the last are
  guaranteed failures and enumerate every valid partial state up to their
  limit. This is inherent to IDDFS on this problem, not an implementation
  defect; plain DFS with backtracking finds a square of order 5 in a few dozen
  nodes.
* **Practical range.** Reduced form: up to `n = 6` (about 10 s); `n = 7` does
  not finish within 60 s. Full grid: up to `n = 5` (about 2 minutes with
  step 1, 10 s with step 5).
* **No constraint propagation** beyond row/column checks (e.g. no forward
  checking of other empty cells), to keep the search a plain IDDFS over single
  assignments.
* The pre-fill (completion) option is an extension beyond the assignment and
  cannot be combined with the reduced form.
