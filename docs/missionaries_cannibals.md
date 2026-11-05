# Problem 4B — Missionaries and Cannibals (Search Tree)

Shared engine, terminology and visualization rules: [search_trees.md](search_trees.md).
Numbers marked **measured** come from running this implementation.

## 1. Problem Description

Three missionaries and three cannibals stand on the left bank of a river with
one boat that holds at most two people. Everyone must reach the right bank.
The boat cannot cross empty, and on neither bank may the cannibals outnumber
the missionaries while at least one missionary is there.

The implementation supports any number of missionaries `M`, cannibals `C` and
boat capacity `K` (`-m`, `-c`, `-b`); the standard problem is `M = C = 3`,
`K = 2`.

## 2. Mathematical Model

State `s = (m, c, b)`: missionaries and cannibals on the **left** bank and the
boat side (`b = 1` left, `b = 0` right). The right bank holds `(M − m, C − c)`.

A crossing carries `(Δm, Δc)` people with `Δm, Δc ≥ 0` and
`1 ≤ Δm + Δc ≤ K`:

```
b = 1 (left → right):  (m, c, 1) → (m − Δm, c − Δc, 0)     requires Δm ≤ m, Δc ≤ c
b = 0 (right → left):  (m, c, 0) → (m + Δm, c + Δc, 1)     requires Δm ≤ M − m, Δc ≤ C − c
```

Safety constraints on the resulting state:

```
(m = 0) ∨ (m ≥ c)                          left bank
(M − m = 0) ∨ (M − m ≥ C − c)              right bank
```

## 3. Problem Representation

[`search_trees/missionaries_cannibals/model.py`](../search_trees/missionaries_cannibals/model.py):
the state is the tuple `(m, c, b)`. Actions are labelled `ΔmMΔcC to R|L`, e.g.
`0M2C to R` = two cannibals cross to the right bank. Text output shows both
banks, e.g. `(3,1,R) 3M1C       ~~~ [boat] 0M2C`.

## 4. Variables and Domains

| Element | Definition |
|---|---|
| Variables | `m ∈ {0..M}`, `c ∈ {0..C}`, `b ∈ {0, 1}` |
| State space | `(M+1)(C+1)·2` combinations: 32 for 3/3 |
| Boat loads | all `(Δm, Δc)` with `1 ≤ Δm + Δc ≤ K`: 5 for `K = 2` — `0M1C, 0M2C, 1M0C, 1M1C, 2M0C` |

## 5. Initial State

`(M, C, 1)` = `(3, 3, L)`. The initial state must itself be safe
(e.g. `M = 1, C = 2` is rejected).

## 6. Goal State

`(0, 0, 0)` = everyone and the boat on the right bank.

## 7. Constraints and Validity Checks

| Check | Effect in the search tree |
|---|---|
| a crossing may not take people who are not on the boat's bank (`0 ≤ m ≤ M`, `0 ≤ c ≤ C`) | not an applicable action; not generated |
| boat carries 1..K people | only such loads are generated |
| safety on both banks | a crossing into an unsafe state is an **invalid transition**: shown in the tree as a red leaf with the reason (e.g. `left bank: 3 cannibals > 2 missionaries`) and never expanded |
| repeated state | **duplicate** leaf, never expanded |

The independent validator
([`validator.py`](../search_trees/missionaries_cannibals/validator.py))
checks a single state (`validate_state`) and a whole solution path
(`validate_solution`): start and end states, safety of every state, the boat
changing sides every step, people moving in the boat's direction only, and the
boat capacity.

## 8. Objective

Reach the goal with the minimum number of crossings; BFS returns such a path.

## 9. State Space and Search-Tree Analysis

**Theoretical (3/3/2):** 32 combinations of `(m, c, b)`, of which 20 are
safe; 5 boat loads, so at most 5 transitions per state.

**Measured:**

| Configuration | Strategy | Crossings | Tree nodes | Expanded | Valid transitions | Invalid | Duplicates | Dead ends | Unique states | Raw BF | Valid BF | Effective BF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3/3/2 | BFS | **11** | 46 | 13 | 28 | 17 | 14 | 2 | 15 | 3.462 | 2.154 | 1.077 |
| 3/3/2 | DFS | 11 | 43 | 12 | 26 | 16 | 12 | 1 | 15 | 3.500 | 2.167 | 1.167 |
| 3/3/2, whole tree (`--explore-all`) | BFS | 11 | 49 | 14 | 30 | 18 | 16 | 3 | **15** | 3.429 | 2.143 | 1.000 |
| 3/3/2, tree search to depth 11 (`--no-duplicate-detection --max-depth 11 --explore-all`) | BFS | 11 | **30,641** | 7,727 | 19,221 | 11,419 | 0 | 0 | 15 | 3.965 | 2.488 | 2.488 |
| 4/4/2 | BFS | **none** | 40 | 11 | 22 | 17 | 12 | 4 | 11 | 3.545 | 2.000 | 0.909 |
| 4/4/3 | BFS | 9 | 106 | 18 | 51 | 54 | 31 | 4 | 21 | 5.833 | 2.833 | 1.111 |
| 5/5/3 | BFS | 11 | 132 | 22 | 61 | 70 | 36 | 5 | 26 | 5.955 | 2.773 | 1.136 |
| 2/2/2 | BFS | 5 | 24 | 8 | 18 | 5 | 9 | 3 | 10 | 2.875 | 2.250 | 1.125 |

New states per depth (3/3/2, whole tree): `1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1`.

Observations:

* Only **15 of the 20 safe states are reachable** from the initial state.
* The state graph is almost a single corridor: after depth 1, every level adds
  one or two new states. The search tree is small because duplicate detection
  cuts every return crossing.
* Without duplicate detection the tree up to depth 11 has **30,641 nodes** and
  contains **4 goal nodes** — the four known optimal 11-crossing solutions.
  With duplicate detection the tree keeps one path to every state, so it shows
  one of them.
* 4 missionaries, 4 cannibals and a boat of 2 have **no solution**: the search
  exhausts the 11 reachable states.

## 10. Algorithm Used

BFS by default (shortest solution); DFS with `--strategy dfs`. Shared
pseudocode: [search_trees.md](search_trees.md).

## 11. Pseudocode (problem-specific part)

```
function EXPAND((m, c, b)):
    sign ← −1 if b = left else +1
    for (Δm, Δc) in loads with 1 ≤ Δm + Δc ≤ K:
        s' ← (m + sign·Δm, c + sign·Δc, 1 − b)
        if s' outside 0..M / 0..C: continue                 // not applicable
        if not SAFE(s'): yield INVALID(action, s', reason)  // shown, never expanded
        else:            yield (action, s')
```

## 12. Implementation and Search-Tree Visualization

Complete tree for 3/3/2 (BFS, `--explore-all`) drawn up to depth 4
(`python main.py missionaries --explore-all --tree-depth 4 --tree-nodes 30 --mermaid tree.md`;
**partial tree**: 19 of 49 nodes):

```mermaid
flowchart TD
    %% Missionaries and Cannibals search tree
    n0["id 0, d=0, START<br/>(3,3,L)<br/>L: 3M 3C | R: 0M 0C"]
    n1["id 1, d=1, dead end<br/>(3,2,R)<br/>L: 3M 2C | R: 0M 1C"]
    n2["id 2, d=1<br/>(3,1,R)<br/>L: 3M 1C | R: 0M 2C"]
    n3["id 3, d=1, invalid<br/>(2,3,R)<br/>L: 2M 3C | R: 1M 0C"]
    n4["id 4, d=1, dead end<br/>(2,2,R)<br/>L: 2M 2C | R: 1M 1C"]
    n5["id 5, d=1, invalid<br/>(1,3,R)<br/>L: 1M 3C | R: 2M 0C"]
    n6["id 6, d=2, duplicate<br/>(3,3,L)<br/>L: 3M 3C | R: 0M 0C"]
    n7["id 7, d=2<br/>(3,2,L)<br/>L: 3M 2C | R: 0M 1C"]
    n8["id 8, d=2, duplicate<br/>(3,3,L)<br/>L: 3M 3C | R: 0M 0C"]
    n9["id 9, d=2, invalid<br/>(2,3,L)<br/>L: 2M 3C | R: 1M 0C"]
    n10["id 10, d=2, duplicate<br/>(3,2,L)<br/>L: 3M 2C | R: 0M 1C"]
    n11["id 11, d=2, duplicate<br/>(3,3,L)<br/>L: 3M 3C | R: 0M 0C"]
    n12["id 12, d=3, duplicate<br/>(3,1,R)<br/>L: 3M 1C | R: 0M 2C"]
    n13["id 13, d=3<br/>(3,0,R)<br/>L: 3M 0C | R: 0M 3C"]
    n14["id 14, d=3, duplicate<br/>(2,2,R)<br/>L: 2M 2C | R: 1M 1C"]
    n15["id 15, d=3, invalid<br/>(2,1,R)<br/>L: 2M 1C | R: 1M 2C"]
    n16["id 16, d=3, invalid<br/>(1,2,R)<br/>L: 1M 2C | R: 2M 1C"]
    n17["id 17, d=4<br/>(3,1,L)<br/>L: 3M 1C | R: 0M 2C"]
    n18["id 18, d=4, duplicate<br/>(3,2,L)<br/>L: 3M 2C | R: 0M 1C"]
    n0 -->|"0M1C to R"| n1
    n0 -->|"0M2C to R"| n2
    n0 -->|"1M0C to R"| n3
    n0 -->|"1M1C to R"| n4
    n0 -->|"2M0C to R"| n5
    n1 -->|"0M1C to L"| n6
    n2 -->|"0M1C to L"| n7
    n2 -->|"0M2C to L"| n8
    n4 -->|"0M1C to L"| n9
    n4 -->|"1M0C to L"| n10
    n4 -->|"1M1C to L"| n11
    n7 -->|"0M1C to R"| n12
    n7 -->|"0M2C to R"| n13
    n7 -->|"1M0C to R"| n14
    n7 -->|"1M1C to R"| n15
    n7 -->|"2M0C to R"| n16
    n13 -->|"0M1C to L"| n17
    n13 -->|"0M2C to L"| n18
    partialNote["Partial tree: 19 of 49 nodes shown (depth at most 4)"]
    class partialNote note
    classDef start fill:#dbeafe,stroke:#1d4ed8,color:#111
    classDef goal fill:#dcfce7,stroke:#15803d,color:#111
    classDef path stroke:#15803d,stroke-width:3px
    classDef duplicate fill:#f3f4f6,stroke:#9ca3af,color:#555,stroke-dasharray:4 3
    classDef invalid fill:#fee2e2,stroke:#b91c1c,color:#111
    classDef cut fill:#fef9c3,stroke:#a16207,color:#111
    classDef note fill:#ffffff,stroke:#ffffff,color:#555
    class n0 start
    class n2 path
    class n3 invalid
    class n5 invalid
    class n6 duplicate
    class n7 path
    class n8 duplicate
    class n9 invalid
    class n10 duplicate
    class n11 duplicate
    class n12 duplicate
    class n13 path
    class n14 duplicate
    class n15 invalid
    class n16 invalid
    class n17 path
    class n18 duplicate
```

The complete 49-node tree as text (`--explore-all --tree-depth 11 --tree-nodes 60`):

```
[0] d=0 (3,3,L) 3M3C [boat] ~~~       0M0C  (INITIAL; on solution path)
|-- [1] d=1 0M1C to R -> (3,2,R) 3M2C       ~~~ [boat] 0M1C  (dead end)
|   `-- [6] d=2 0M1C to L -> (3,3,L) 3M3C [boat] ~~~       0M0C  (duplicate; state already generated at depth 0)
|-- [2] d=1 0M2C to R -> (3,1,R) 3M1C       ~~~ [boat] 0M2C  (on solution path)
|   |-- [7] d=2 0M1C to L -> (3,2,L) 3M2C [boat] ~~~       0M1C  (on solution path)
|   |   |-- [12] d=3 0M1C to R -> (3,1,R) 3M1C       ~~~ [boat] 0M2C  (duplicate; state already generated at depth 1)
|   |   |-- [13] d=3 0M2C to R -> (3,0,R) 3M0C       ~~~ [boat] 0M3C  (on solution path)
|   |   |   |-- [17] d=4 0M1C to L -> (3,1,L) 3M1C [boat] ~~~       0M2C  (on solution path)
|   |   |   |   |-- [19] d=5 0M1C to R -> (3,0,R) 3M0C       ~~~ [boat] 0M3C  (duplicate; state already generated at depth 3)
|   |   |   |   |-- [20] d=5 1M0C to R -> (2,1,R) 2M1C       ~~~ [boat] 1M2C  (invalid; right bank: 2 cannibals > 1 missionaries)
|   |   |   |   |-- [21] d=5 1M1C to R -> (2,0,R) 2M0C       ~~~ [boat] 1M3C  (invalid; right bank: 3 cannibals > 1 missionaries)
|   |   |   |   `-- [22] d=5 2M0C to R -> (1,1,R) 1M1C       ~~~ [boat] 2M2C  (on solution path)
|   |   |   |       |-- [23] d=6 0M1C to L -> (1,2,L) 1M2C [boat] ~~~       2M1C  (invalid; left bank: 2 cannibals > 1 missionaries)
|   |   |   |       |-- [24] d=6 0M2C to L -> (1,3,L) 1M3C [boat] ~~~       2M0C  (invalid; left bank: 3 cannibals > 1 missionaries)
|   |   |   |       |-- [25] d=6 1M0C to L -> (2,1,L) 2M1C [boat] ~~~       1M2C  (invalid; right bank: 2 cannibals > 1 missionaries)
|   |   |   |       |-- [26] d=6 1M1C to L -> (2,2,L) 2M2C [boat] ~~~       1M1C  (on solution path)
|   |   |   |       |   |-- [28] d=7 0M1C to R -> (2,1,R) 2M1C       ~~~ [boat] 1M2C  (invalid; right bank: 2 cannibals > 1 missionaries)
|   |   |   |       |   |-- [29] d=7 0M2C to R -> (2,0,R) 2M0C       ~~~ [boat] 1M3C  (invalid; right bank: 3 cannibals > 1 missionaries)
|   |   |   |       |   |-- [30] d=7 1M0C to R -> (1,2,R) 1M2C       ~~~ [boat] 2M1C  (invalid; left bank: 2 cannibals > 1 missionaries)
|   |   |   |       |   |-- [31] d=7 1M1C to R -> (1,1,R) 1M1C       ~~~ [boat] 2M2C  (duplicate; state already generated at depth 5)
|   |   |   |       |   `-- [32] d=7 2M0C to R -> (0,2,R) 0M2C       ~~~ [boat] 3M1C  (on solution path)
|   |   |   |       |       |-- [33] d=8 0M1C to L -> (0,3,L) 0M3C [boat] ~~~       3M0C  (on solution path)
|   |   |   |       |       |   |-- [37] d=9 0M1C to R -> (0,2,R) 0M2C       ~~~ [boat] 3M1C  (duplicate; state already generated at depth 7)
|   |   |   |       |       |   `-- [38] d=9 0M2C to R -> (0,1,R) 0M1C       ~~~ [boat] 3M2C  (on solution path)
|   |   |   |       |       |       |-- [39] d=10 0M1C to L -> (0,2,L) 0M2C [boat] ~~~       3M1C  (on solution path)
|   |   |   |       |       |       |   |-- [44] d=11 0M1C to R -> (0,1,R) 0M1C       ~~~ [boat] 3M2C  (duplicate; state already generated at depth 9)
|   |   |   |       |       |       |   `-- [45] d=11 0M2C to R -> (0,0,R) 0M0C       ~~~ [boat] 3M3C  (GOAL)
|   |   |   |       |       |       |-- [40] d=10 0M2C to L -> (0,3,L) 0M3C [boat] ~~~       3M0C  (duplicate; state already generated at depth 8)
|   |   |   |       |       |       |-- [41] d=10 1M0C to L -> (1,1,L) 1M1C [boat] ~~~       2M2C  (dead end)
|   |   |   |       |       |       |   |-- [46] d=11 0M1C to R -> (1,0,R) 1M0C       ~~~ [boat] 2M3C  (invalid; right bank: 3 cannibals > 2 missionaries)
|   |   |   |       |       |       |   |-- [47] d=11 1M0C to R -> (0,1,R) 0M1C       ~~~ [boat] 3M2C  (duplicate; state already generated at depth 9)
|   |   |   |       |       |       |   `-- [48] d=11 1M1C to R -> (0,0,R) 0M0C       ~~~ [boat] 3M3C  (duplicate; state already generated at depth 11)
|   |   |   |       |       |       |-- [42] d=10 1M1C to L -> (1,2,L) 1M2C [boat] ~~~       2M1C  (invalid; left bank: 2 cannibals > 1 missionaries)
|   |   |   |       |       |       `-- [43] d=10 2M0C to L -> (2,1,L) 2M1C [boat] ~~~       1M2C  (invalid; right bank: 2 cannibals > 1 missionaries)
|   |   |   |       |       |-- [34] d=8 1M0C to L -> (1,2,L) 1M2C [boat] ~~~       2M1C  (invalid; left bank: 2 cannibals > 1 missionaries)
|   |   |   |       |       |-- [35] d=8 1M1C to L -> (1,3,L) 1M3C [boat] ~~~       2M0C  (invalid; left bank: 3 cannibals > 1 missionaries)
|   |   |   |       |       `-- [36] d=8 2M0C to L -> (2,2,L) 2M2C [boat] ~~~       1M1C  (duplicate; state already generated at depth 6)
|   |   |   |       `-- [27] d=6 2M0C to L -> (3,1,L) 3M1C [boat] ~~~       0M2C  (duplicate; state already generated at depth 4)
|   |   |   `-- [18] d=4 0M2C to L -> (3,2,L) 3M2C [boat] ~~~       0M1C  (duplicate; state already generated at depth 2)
|   |   |-- [14] d=3 1M0C to R -> (2,2,R) 2M2C       ~~~ [boat] 1M1C  (duplicate; state already generated at depth 1)
|   |   |-- [15] d=3 1M1C to R -> (2,1,R) 2M1C       ~~~ [boat] 1M2C  (invalid; right bank: 2 cannibals > 1 missionaries)
|   |   `-- [16] d=3 2M0C to R -> (1,2,R) 1M2C       ~~~ [boat] 2M1C  (invalid; left bank: 2 cannibals > 1 missionaries)
|   `-- [8] d=2 0M2C to L -> (3,3,L) 3M3C [boat] ~~~       0M0C  (duplicate; state already generated at depth 0)
|-- [3] d=1 1M0C to R -> (2,3,R) 2M3C       ~~~ [boat] 1M0C  (invalid; left bank: 3 cannibals > 2 missionaries)
|-- [4] d=1 1M1C to R -> (2,2,R) 2M2C       ~~~ [boat] 1M1C  (dead end)
|   |-- [9] d=2 0M1C to L -> (2,3,L) 2M3C [boat] ~~~       1M0C  (invalid; left bank: 3 cannibals > 2 missionaries)
|   |-- [10] d=2 1M0C to L -> (3,2,L) 3M2C [boat] ~~~       0M1C  (duplicate; state already generated at depth 2)
|   `-- [11] d=2 1M1C to L -> (3,3,L) 3M3C [boat] ~~~       0M0C  (duplicate; state already generated at depth 0)
`-- [5] d=1 2M0C to R -> (1,3,R) 1M3C       ~~~ [boat] 2M0C  (invalid; left bank: 3 cannibals > 1 missionaries)
(Complete tree: 49 nodes.)
```

## 13. Complexity Analysis

* With duplicate detection the work is linear in the number of reachable
  states (15) times the number of boat loads (5).
* Without it the tree grows as `O(b^d)`: measured 30,641 nodes at depth 11
  with an effective branching factor of 2.49.
* Larger `M`, `C`, `K` grow the state space as `O(M·C)` and the loads as
  `O(K²)`.

## 14. Test Results

`python -m pytest -v tests/test_missionaries_cannibals.py`: **23 tests,
23 passed, 0 failed** (0.9 s).

| Test class | Tests | What is verified |
|---|---|---|
| `TestModel` | 9 | invalid configurations (negative counts, capacity 0, no people, booleans, unsafe initial state), safety of both banks, boat loads, invalid crossings with reasons, no crossing takes absent people |
| `TestSearchTree` | 9 | 11-crossing BFS solution validated, DFS solution validated, 15 reachable / 20 safe / 32 total states, invalid nodes are never expanded and every valid node is safe, 4/4/2 unsolvable, 1/1/2, 2/2/2, 4/4/3 and 5/5/3 solved and validated |
| `TestValidator` | 2 | state errors and path errors (wrong end, over capacity, boat not changing sides) |
| `TestCLI` | 3 | default run, unsolvable configuration, invalid configuration |

## 15. Execution Example

```
python main.py missionaries
```

```
Solution (11 crossings):
  d= 0 start      (3,3,L) 3M3C [boat] ~~~       0M0C
  d= 1 0M2C to R  (3,1,R) 3M1C       ~~~ [boat] 0M2C
  d= 2 0M1C to L  (3,2,L) 3M2C [boat] ~~~       0M1C
  d= 3 0M2C to R  (3,0,R) 3M0C       ~~~ [boat] 0M3C
  d= 4 0M1C to L  (3,1,L) 3M1C [boat] ~~~       0M2C
  d= 5 2M0C to R  (1,1,R) 1M1C       ~~~ [boat] 2M2C
  d= 6 1M1C to L  (2,2,L) 2M2C [boat] ~~~       1M1C
  d= 7 2M0C to R  (0,2,R) 0M2C       ~~~ [boat] 3M1C
  d= 8 0M1C to L  (0,3,L) 0M3C [boat] ~~~       3M0C
  d= 9 0M2C to R  (0,1,R) 0M1C       ~~~ [boat] 3M2C
  d=10 0M1C to L  (0,2,L) 0M2C [boat] ~~~       3M1C
  d=11 0M2C to R  (0,0,R) 0M0C       ~~~ [boat] 3M3C
Independent validation: PASSED
```

```
python main.py missionaries -m 4 -c 4 -b 2        # no solution (exit code 1)
python main.py missionaries -m 5 -c 5 -b 3        # 11 crossings
python main.py missionaries --no-duplicate-detection --max-depth 11 --explore-all --tree-depth 2
```

## 16. Limitations

* With duplicate detection the tree keeps only the first path to each state, so
  it shows one optimal solution; use tree search with a depth limit to see all
  of them.
* The standard rule is modelled: on each bank, missionaries must not be
  outnumbered when present. Variants (e.g. counting the boat's passengers on
  the arrival bank before they land) are not modelled.
