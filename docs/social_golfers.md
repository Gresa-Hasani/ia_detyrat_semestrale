# Problem 1 — Social Golfers Problem (DFS with Backtracking)

All numbers in this document labelled **measured** were produced by running the
implementation in this repository (Python 3.13.1, Windows 11). Numbers labelled
**theoretical** come from closed-form formulas in
[`social_golfers/landscape.py`](../social_golfers/landscape.py). Elapsed times
depend on the machine; every other measured value is deterministic.

---

## 1. Problem Description

32 golfers play golf once a week, always in groups of 4. For how many weeks can
they play so that no two golfers play in the same group more than once?

Generalised: can `n = g × p` golfers be scheduled into `g` groups of `p`
golfers for `w` weeks so that no two golfers share a group more than once?
The task is to find the **largest** such `w`.

Example week from the assignment (n = 32, g = 8, p = 4) — the validator
confirms that it is a valid week (`test_assignment_example_week_is_valid`):

| Week | Group 1 | Group 2 | Group 3 | Group 4 | Group 5 | Group 6 | Group 7 | Group 8 |
|---|---|---|---|---|---|---|---|---|
| 1 | 0,1,2,3 | 4,5,22,23 | 6,7,20,21 | 8,25,26,27 | 9,10,11,24 | 12,13,15,30 | 14,28,29,31 | 16,17,18,19 |

## 2. Mathematical Model

Let `G = {0, 1, …, n−1}` be the set of golfers. A **week** is a partition of
`G` into `g` disjoint blocks (groups) of size `p`:

```
W = {B_1, …, B_g},   B_k ⊆ G,   |B_k| = p,   B_i ∩ B_j = ∅ (i ≠ j),   ∪ B_k = G
```

A **schedule** of length `w` is a sequence `S = (W_1, …, W_w)` of weeks. For a
pair `{a, b}` let

```
m_ab(S) = | { t : ∃ B ∈ W_t with a, b ∈ B } |
```

be the number of weeks in which `a` and `b` share a group. The problem is

```
maximise  w   subject to   m_ab(S) ≤ 1   for every pair {a, b} ⊆ G.
```

This is a **Constraint Satisfaction Problem (CSP)** for a fixed `w`
("does a feasible schedule exist?") wrapped in an optimisation over `w`.

### Theoretical upper bounds on `w`

* **Counting bound.** Each week golfer `a` meets `p − 1` new partners, and
  there are only `n − 1` possible partners, so
  `w ≤ ⌊(n − 1) / (p − 1)⌋`. Equivalently, there are `C(n,2)` pairs and each
  week uses `g · C(p,2)` of them: `w ≤ C(n,2) / (g · C(p,2)) = (n−1)/(p−1)`.
* **Pigeonhole bound.** In week 2 every group must take its `p` golfers from
  `p` *different* week-1 groups. If `p > g` this is impossible, so `w ≤ 1`.

For the assignment instance: `w ≤ ⌊31 / 3⌋ = 10`.

## 3. Problem Representation

Each week is stored as a list of `g` groups; each group is a list of `p`
golfer ids. Because a week is a *set* partition, the implementation always
uses its **canonical form**:

* golfers are in ascending order inside each group;
* groups are ordered by their smallest golfer, so the first slot of each group
  holds the smallest golfer not yet placed in that week.

Every partition has exactly one canonical form, so this removes duplicate
representations of the same week without losing any solution.

Internally the solver also keeps, for speed:

* `met[i]` — an `n`-bit integer whose bit `j` is set if golfers `i` and `j`
  have already shared a group;
* `week_used[t]` — an `n`-bit integer of the golfers already placed in week `t`.

## 4. Variables and Domains

| Element | Definition |
|---|---|
| Variables | `x[t][k][s]`: the golfer in slot `s` of group `k` in week `t`, with `0 ≤ t < w`, `0 ≤ k < g`, `0 ≤ s < p`. Total: `n · w` variables. |
| Domains | `D(x[t][k][s]) = {0, 1, …, n−1}` |
| Effective domain during search | golfers not yet placed in week `t`, larger than `x[t][k][s−1]`, and with no previous meeting with any golfer already in group `k`. For `s = 0` the domain shrinks to a single value: the smallest unplaced golfer. |

## 5. Initial State

The empty schedule: no variable assigned. With symmetry breaking enabled (the
default), week 1 is fixed to the canonical partition
`{0,…,p−1}, {p,…,2p−1}, …`, so the search starts from a state with `n`
assigned variables (see Section 12 for why this is sound).

## 6. Goal State

A complete assignment of all `n · w` variables that satisfies every constraint
(C1–C5). For the optimisation version, the goal is a feasible schedule with
the largest `w`. A goal is **proven optimal** when `w` equals the theoretical
upper bound, or when the search for `w + 1` weeks completes without hitting a
limit and finds nothing.

## 7. Constraints

All are **hard constraints**:

| Id | Constraint | Formal statement | Where enforced |
|---|---|---|---|
| C1 | Every golfer belongs to exactly one group per week | `∀t, ∀a: |{k : a ∈ B_{t,k}}| = 1` | solver: `week_used` bitmask; validator: per-week `Counter` |
| C2 | Every group contains exactly `p` golfers | `|B_{t,k}| = p` | solver: slot structure; validator: group length |
| C3 | Exactly `g` groups per week | `|W_t| = g` | solver: slot structure; validator: week length |
| C4 | No pair together more than once | `m_ab(S) ≤ 1` | solver: `met[c] & group_mask == 0` before each assignment; validator: pair `Counter` |
| C5 | Every produced week satisfies C1–C4 | — | checked incrementally by the solver, re-checked from scratch by the validator |

## 8. Objective Function

**Hard constraints** decide whether a schedule is allowed at all. The
**objective function** ranks allowed schedules.

For a schedule `S = (W_1, …, W_m)` the implementation
([`objective.py`](../social_golfers/objective.py)) defines:

```
f(S) = max { k : (W_1, …, W_k) satisfies C1–C4 }      (longest valid prefix)
V(S) = Σ_{a<b} max(0, m_ab(S) − 1)                     (repeated-pair penalty)
```

The optimisation problem is `maximise f(S)`. For any feasible schedule
`f(S) = |S|`, the number of weeks.

* **Feasible solution:** a schedule satisfying all hard constraints, i.e.
  `f(S) = |S|` (which implies `V(S) = 0`).
* **Optimal solution:** a feasible schedule with the maximum possible number of
  weeks. For 32-8-4 this is 10 weeks (it reaches the counting bound; this
  known result is from the literature and was **not** reproduced by this
  implementation — see Section 16).

Inside DFS every node is already a feasible partial schedule, so `f` simply
equals the number of completed weeks. The solver evaluates it each time a week
is completed (`fitness_evaluations`) and keeps the best schedule seen.

## 9. Landscape Calculation

### 9.1 Theoretical landscape

| Quantity | Formula | Meaning |
|---|---|---|
| Naive assignments | `n^(n·w)` | every variable takes any value from its domain |
| Permutation schedules | `(n!)^w` | every week is a permutation of the golfers (C1 enforced) |
| Partitions per week | `P = n! / ((p!)^g · g!)` | distinct weeks: order inside groups and order of groups do not matter |
| Partition schedules | `P^w` | sequences of `w` weeks |
| Canonical schedules | `C(P−1, w−1)` | week 1 fixed, the remaining `w−1` weeks a *set* of distinct partitions (equal weeks would repeat pairs) — an upper bound on candidate states before C4 is applied |
| Search depth | `n · w` slots (`n · (w−1)` with week 1 fixed) | depth of a complete schedule in the search tree |
| Maximum branching factor | `n − 1` | slot 2 of group 1 (any golfer except golfer 0); slot 1 of every group has branching factor 1 (forced) |

**Theoretical** values (computed by `compute_theoretical_landscape`):

| n | g | p | w | Upper bound | P (partitions/week) | P^w | C(P−1, w−1) | n^(n·w) | (n!)^w | Depth |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 2 | 2 | 3 | 3 | 3 | 27 | 1 | 16,777,216 | 13,824 | 12 |
| 6 | 3 | 2 | 5 | 5 | 15 | 759,375 | 1,001 | 2.210e+23 | 1.934e+14 | 30 |
| 9 | 3 | 3 | 4 | 4 | 280 | 6,146,560,000 | 3,580,779 | 2.252e+34 | 1.734e+22 | 36 |
| 12 | 4 | 3 | 5 | 5 | 15,400 | 8.661e+20 | 2.342e+15 | 5.634e+64 | 2.521e+43 | 60 |
| 16 | 4 | 4 | 5 | 5 | 2,627,625 | 1.252e+32 | 1.986e+24 | 2.135e+96 | 4.009e+66 | 80 |
| 32 | 8 | 4 | 10 | 10 | 5.928e+19 | 5.365e+197 | 2.493e+172 | 4.446e+481 | 1.591e+354 | 320 |

Large values are shown as truncated mantissa × power of ten.

### 9.2 Measured landscape

Measured by the DFS solver (`SearchStats`), limit 2,000,000 expanded states.
"SB" = symmetry breaking; "count all" = the search does not stop at the first
solution and counts every goal state.

| n-g-p | target w | SB | mode | best w | completed | proven max | states expanded | assignments | backtracks | C4 rejections | group FC rej. | week FC rej. | symmetry rej. | validity ratio | raw BF | effective BF | max depth | solutions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4-2-2 | 3 | on | count all | 3 | yes | yes | 12 | 12 | 12 | 5 | 0 | 0 | 1 | 0.667 | 1.500 | 1.000 | 12 | 1 |
| 4-2-2 | 3 | off | count all | 3 | yes | yes | 50 | 55 | 55 | 15 | 0 | 0 | 0 | 0.786 | 1.400 | 1.100 | 12 | 6 |
| 6-3-2 | 5 | on | count all | 5 | yes | yes | 186 | 187 | 187 | 119 | 0 | 24 | 40 | 0.505 | 1.989 | 1.005 | 30 | 2 |
| 6-3-2 | 5 | off | count all | 5 | yes | yes | 10,512 | 11,231 | 11,231 | 7,485 | 0 | 870 | 0 | 0.573 | 1.863 | 1.068 | 30 | 720 |
| 9-3-3 | 4 | on | first | 4 | yes | yes | 27 | 27 | 0 | 21 | 1 | 0 | 0 | 0.551 | 1.815 | 1.000 | 36 | 1 |
| 9-3-3 | 4 | off | first | 4 | yes | yes | 36 | 36 | 0 | 21 | 1 | 0 | 0 | 0.621 | 1.611 | 1.000 | 36 | 1 |
| 10-5-2 | 9 | on | first | 9 | yes | yes | 84 | 84 | 4 | 76 | 0 | 14 | 0 | 0.483 | 2.071 | 1.000 | 90 | 1 |
| 16-4-4 | 5 | on | first | 5 | yes | yes | 64 | 64 | 0 | 84 | 0 | 0 | 0 | 0.432 | 2.312 | 1.000 | 80 | 1 |
| 6-2-3 | 2 | on | first | 1 | yes | yes | 2 | 1 | 1 | 2 | 3 | 0 | 0 | 0.167 | 3.000 | 0.500 | 7 | 0 |
| 12-4-3 | 5 | on | first | 4 | yes | yes | 906,200 | 906,199 | 906,199 | 1,327,301 | 427,854 | 302,868 | 97,200 | 0.296 | 3.378 | 1.000 | 53 | 0 |
| 32-8-4 | 10 | on | first | 5 | no (node limit) | no | 2,000,000 | 2,000,000 | 1,999,880 | 6,406,010 | 2,125,445 | 1,439,888 | 0 | 0.167 | 5.986 | 1.000 | 162 | 0 |
| 32-8-4 | 10 | on | first | 5 | no (20M node limit) | no | 20,000,000 | 20,000,000 | 19,999,877 | 49,060,861 | 25,204,335 | 10,405,587 | 0 | 0.191 | 5.234 | 1.000 | 162 | 0 |

The last row (command `python main.py golfers -g 8 -p 4 --max-nodes 20000000 --time-limit 0`,
199.8 s) completed **125,134 distinct 5-week schedules** (fitness evaluations
at week 5), and none of them could be extended to a 6th week. Accepted nodes
per week: `0, 32, 32, 32, 19,556,029, 443,875, 0, 0, 0, 0`. Weeks 2–4 were
never revised: all the effort went into weeks 5 and 6 (see Section 16).

Definitions of the measured values:

* **states expanded** — states whose successors were generated (calls of the
  expansion routine);
* **assignments** — candidates that passed every check and became search nodes;
* **backtracks** — assignments that were undone;
* **validity ratio** — `assignments / candidates generated`;
* **raw BF** — `candidates generated / states expanded`;
* **effective BF** — `assignments / states expanded` (in "count all" mode it
  can exceed 1 because goal leaves are not expanded further);
* **max depth** — the largest number of filled slots reached.

**Valid states (measured, exhaustive).** For small instances the complete
pruned space was enumerated and the counts agree with known combinatorics:

* 4-2-2: K4 has 3 perfect matchings, so there are `3! = 6` ordered 3-week
  schedules; with symmetry breaking exactly 1 canonical schedule remains.
* 6-3-2: K6 has 6 one-factorisations, so there are `6 · 5! = 720` ordered
  5-week schedules; each perfect matching lies in exactly 2 of them, so 2
  canonical schedules remain with week 1 fixed and weeks ordered.
* 12-4-3: the exhaustive search (906,200 states) proves that **4 weeks is the
  maximum**, one less than the counting bound of 5.

### 9.3 Interpretation

* The theoretical space is astronomically large (`10^481` naive assignments for
  32-8-4), but canonical representation, symmetry breaking and incremental
  constraint checking cut it down so far that 9-3-3 and 16-4-4 are solved with
  **zero backtracks** (27 and 64 states).
* Symmetry breaking reduces the 6-3-2 exhaustive search from 10,512 to 186
  states (×56.5) while keeping the same optimum.
* The candidate validity ratio drops as the instance grows (0.67 → 0.17): the
  deeper the schedule, the more pairs are already used and the more
  candidates C4 rejects.

## 10. Algorithm Used — Depth First Search with Backtracking

DFS is a natural fit:

* A schedule is built by a **sequence of decisions** (one golfer per slot) of
  known, fixed depth `n · w`; DFS explores exactly this kind of tree.
* **Memory** is linear in depth (`O(n · w)`), whereas BFS would have to store
  a whole level of an exponentially wide tree.
* Constraints can be checked **incrementally**: a violation in a partial
  schedule can never be repaired by later assignments, so the whole subtree
  can be pruned immediately (backtracking).
* DFS reaches complete weeks quickly, so it always has a good "best so far"
  schedule when a limit stops it.

DFS is **uninformed**: candidates are tried in ascending order with no
heuristic, as required by the assignment topic (uninformed search).

## 11. Pseudocode

```
function SOLVE(g, p, target_w, limits):
    n ← g · p
    schedule ← empty; met[i] ← ∅ for all i; best ← empty
    if symmetry_breaking:
        week 1 ← {0..p−1}, {p..2p−1}, …          // relabelling symmetry
        RECORD_WEEK(1)
        EXTEND(week=2, group=1, slot=1)
    else:
        EXTEND(week=1, group=1, slot=1)
    return best, statistics

function EXTEND(t, k, s):
    CHECK_LIMITS()                                // node / time limit
    B ← schedule[t][k]                            // golfers already in the group
    if s = 1: candidates ← { smallest golfer not yet placed in week t }
    else:     candidates ← { c > last(B) : c not placed in week t }   // ascending
    for c in candidates:
        if met[c] ∩ B ≠ ∅:                    continue      // C4 violated
        if SB and t ≥ 3 and k = 1 and s = 2 and c ≤ schedule[t−1][1][2]:
                                              continue      // week order
        if fewer than p−|B|−1 golfers > c remain compatible with B ∪ {c}:
                                              continue      // group forward check
        PLACE(c)                                  // update schedule, met, week_used
        if group closed and another group follows and
           some unplaced golfer has < p−1 compatible unplaced golfers:
            UNDO(c); continue                     // week forward check
        if s < p:        stop ← EXTEND(t, k, s+1)
        else if k < g:   stop ← EXTEND(t, k+1, 1)
        else:
            stop ← RECORD_WEEK(t)                 // evaluate f, keep best
            if not stop and t < target_w: stop ← EXTEND(t+1, 1, 1)
        if stop: return true
        UNDO(c)                                   // backtrack
    return false

function RECORD_WEEK(t):
    if t > |best|: best ← copy of weeks 1..t
    return t = target_w and not count_all
```

## 12. Implementation Explanation

| File | Responsibility |
|---|---|
| [`model.py`](../social_golfers/model.py) | `GolferConfig` (g, p, n = g·p), input validation, theoretical week bounds |
| [`solver.py`](../social_golfers/solver.py) | `SocialGolfersDFS`: DFS with backtracking, pruning, limits, `SearchStats`, `SearchResult` |
| [`validator.py`](../social_golfers/validator.py) | independent validator (sets and a pair `Counter`, no bitmasks, no shared code with the solver) |
| [`objective.py`](../social_golfers/objective.py) | objective `f(S)` and penalty `V(S)` |
| [`landscape.py`](../social_golfers/landscape.py) | theoretical landscape formulas |
| [`report.py`](../social_golfers/report.py) | text tables of schedules, landscape and statistics |
| [`cli.py`](../social_golfers/cli.py) | command-line interface |

Key points:

1. **Bitmask constraint checks.** `met[c] & group_mask` tests C4 against all
   group members in one integer operation; `week_used` enforces C1.
2. **Backtracking** undoes exactly what an assignment changed: the slot, the
   week-usage bit and the pair bits. Because C4 guarantees the pair bits were
   not set before, clearing them restores the previous state exactly.
3. **Pruning** — four rejection reasons are counted separately: pair conflict
   (C4), week-order symmetry, group forward check, week forward check. Both
   forward checks test *necessary* conditions only, so they never remove a
   solution (confirmed by the unchanged exhaustive counts 6/1 and 720/2).
4. **Symmetry breaking (sound).** Relabelling golfers maps any solution to one
   whose week 1 is `{0..p−1}, {p..2p−1}, …`; reordering weeks 2..w by the
   smallest partner of golfer 0 (distinct in every week, because golfer 0
   never meets the same golfer twice) gives a strictly increasing order. Every
   solution therefore has a representative the search still explores.
   `--no-symmetry-breaking` disables both rules for comparison.
5. **Limits.** `max_nodes` (expanded states) and `time_limit` (seconds) stop
   the search; the best schedule found so far is returned with
   `search_completed = False`.
6. **Maximisation.** The default target is the theoretical upper bound; DFS
   keeps the deepest feasible schedule, so the result is the maximum number of
   weeks found within the limits.
7. **Independent validation.** The CLI validates every result with
   `validate_schedule` and exits with code 1 if validation fails.

## 13. Complexity Analysis

Let `d = n · (w − 1)` be the search depth (week 1 fixed) and `b ≤ n − 1` the
branching factor.

* **Time (worst case):** `O(b^d)` nodes. A tighter bound uses the
  representation: at most `C(P−1, w−1)` canonical schedules, with
  `P = n!/((p!)^g g!)`. Both are exponential; the decision version of the
  SGP is believed to be computationally hard in general and no polynomial
  algorithm is known.
* **Cost per node:** candidate generation `O(n)` bit operations on `n`-bit
  integers; C4 check `O(1)` integer operations; group forward check `O(p)`;
  week forward check `O(n)` (only when a group is closed).
* **Space:** `O(n · w)` for the recursion stack and the schedule, plus `O(n)`
  bitmasks of `n` bits each. DFS never stores the frontier.
* **Measured growth:** 9 golfers need 27 states, 12 golfers need 906,200 states
  for a complete proof, and 32 golfers do not finish within 2,000,000 states.

## 14. Test Results

Command: `python -m pytest -v` (file `tests/test_social_golfers.py`).

Measured result: **68 tests collected, 68 passed, 0 failed, 6.78 s**
(Python 3.13.1, pytest 9.0.2). The slowest test is the exhaustive 12-4-3 proof
(about 5 s).

| Test class | Tests | What is verified |
|---|---|---|
| `TestConfiguration` | 23 | parameters, n = g·p check, upper bounds, invalid targets and limits |
| `TestValidator` | 9 | assignment example week, valid and broken schedules |
| `TestObjective` | 3 | f(S) longest valid prefix, penalty V(S) |
| `TestLandscape` | 6 | partition counts and all formulas for 32-8-4 |
| `TestDFSSolver` | 21 | optimality, exhaustive counts, unsolvable targets, limits, statistics, canonical form |
| `TestReport` | 1 | formatting of numbers too large for a float |
| `TestCLI` | 5 | CLI output, solution counting, error exit code, bound warning |

Covered areas: configuration validation (n ≠ g·p, g < 1, p < 2, non-integers,
booleans), invalid targets and limits, the validator on valid and broken
schedules (wrong group count/size, missing/duplicate golfers, out-of-range and
non-integer ids, repeated pairs, malformed structures), the objective function,
exact landscape formulas, solver optimality on 5 instances, exhaustive solution
counts, unsolvable targets, the 12-4-3 optimality proof, node and time limits,
the full 32-8-4 instance, statistic consistency, canonical form and the CLI.

## 15. Execution Examples

```
python main.py golfers -g 3 -p 3
```

```
Social Golfers Problem: n=9, g=3, p=3, target w=4
...
Measured search statistics (DFS with backtracking):
  Weeks found (objective f)     : 4 (target 4)
  Target reached                : yes
  Search completed              : yes
  Proven maximum                : yes
  States expanded               : 27
  Backtracks                    : 0
  Independent validation        : PASSED

Best schedule (4 weeks):
Week    | Group 1 | Group 2 | Group 3
-------------------------------------
Week 1  | 0,1,2   | 3,4,5   | 6,7,8
Week 2  | 0,3,6   | 1,4,7   | 2,5,8
Week 3  | 0,4,8   | 1,5,6   | 2,3,7
Week 4  | 0,5,7   | 1,3,8   | 2,4,6
```

The assignment instance (32 golfers), default limits (2,000,000 states, 60 s):

```
python main.py golfers -g 8 -p 4
```

Best schedule found (5 weeks, validated):

```
Week    | Group 1   | Group 2   | Group 3   | Group 4     | Group 5     | Group 6     | Group 7     | Group 8
Week 1  | 0,1,2,3   | 4,5,6,7   | 8,9,10,11 | 12,13,14,15 | 16,17,18,19 | 20,21,22,23 | 24,25,26,27 | 28,29,30,31
Week 2  | 0,4,8,12  | 1,5,9,13  | 2,6,10,14 | 3,7,11,15   | 16,20,24,28 | 17,21,25,29 | 18,22,26,30 | 19,23,27,31
Week 3  | 0,5,10,15 | 1,4,11,14 | 2,7,8,13  | 3,6,9,12    | 16,21,26,31 | 17,20,27,30 | 18,23,24,29 | 19,22,25,28
Week 4  | 0,6,11,13 | 1,7,10,12 | 2,4,9,15  | 3,5,8,14    | 16,22,27,29 | 17,23,26,28 | 18,20,25,31 | 19,21,24,30
Week 5  | 0,7,9,14  | 1,6,8,15  | 2,5,11,12 | 3,4,10,13   | 16,23,25,30 | 17,22,24,31 | 18,21,27,28 | 19,20,26,29
```

Other useful commands:

```
python main.py golfers -g 3 -p 2 --count-solutions            # 2 canonical schedules
python main.py golfers -g 3 -p 2 --count-solutions --no-symmetry-breaking   # 720
python main.py golfers -g 4 -p 3 --max-nodes 0 --time-limit 0  # proves max = 4
python main.py golfers -g 8 -p 4 -w 5                          # fixed target
python main.py golfers -g 8 -p 4 -n 30                         # error: n != g x p
```

## 16. Implementation Limitations

* **32-8-4 reaches 5 weeks, not the optimum of 10.** The analysis below was
  checked with an independent brute-force script. In the 5-week prefix DFS
  builds first, golfers 0–15 and golfers 16–31 form two separate complete
  designs: golfer 0 has met all of 1–15, and every pair inside 16–31 has
  already been used. No group containing golfer 0 can be formed in week 6, so
  the prefix is a dead end. Uninformed DFS only discovers this by exhausting
  the entire week-5 subtree before it revises week 2 (**thrashing**). Reaching
  10 weeks requires techniques outside uninformed search (strong value/variable
  ordering heuristics, constraint propagation over the whole schedule, or
  algebraic constructions).
* "Proven maximum" depends on exhaustive search, which is feasible only for
  small instances (e.g. 12-4-3 in about 6 s).
* With symmetry breaking on, `--count-solutions` counts canonical schedules
  (week 1 fixed, weeks ordered), not schedules up to full isomorphism.
* `p ≥ 2` is required: with `p = 1` there are no pairs and the number of weeks
  is unbounded.
* The recursion depth is `n · w`; the solver temporarily raises Python's
  recursion limit accordingly, so very large instances may be limited by
  memory and speed (pure Python, about 10 µs per expanded state).
