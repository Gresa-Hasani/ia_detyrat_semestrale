# Final Implementation Report — Assignment 1 (Uninformed Search Techniques)

Assignment: [Detyra1.md](https://github.com/adrianymeri/Artificial-Intelligence-2026/blob/main/Detyra1.md).
Verification environment: Python 3.13.1, pytest 9.0.2, Windows 11. Every
number in this report was produced by running the code in this repository
during the final verification.

## 1. Summary

All four assignment problems are implemented with the required algorithms,
each with an independent validator, automated tests, a command-line interface
and English documentation.

| # | Problem | Required algorithm | Package | Documentation |
|---|---|---|---|---|
| 1 | Social Golfers Problem | DFS with Backtracking | `social_golfers/` | [social_golfers.md](social_golfers.md) |
| 2 | Sudoku Solver (Easy, Medium, Hard) | BFS with Backtracking | `sudoku/` | [sudoku.md](sudoku.md) |
| 3 | Latin Square | IDDFS with Backtracking | `latin_square/` | [latin_square.md](latin_square.md) |
| 4 | Search Trees: 8-Puzzle, Missionaries and Cannibals, Rotating Workforce Scheduling | search-tree construction (BFS / DFS) | `search_trees/` | [search_trees.md](search_trees.md), [eight_puzzle.md](eight_puzzle.md), [missionaries_cannibals.md](missionaries_cannibals.md), [workforce_scheduling.md](workforce_scheduling.md) |

## 2. Requirements Coverage (Detyra1.md)

| Requirement | Social Golfers | Sudoku | Latin Square | Search Trees |
|---|---|---|---|---|
| Model the problem | CSP: weeks as set partitions, constraints C1–C5 (doc §2, §7) | CSP: 81 cells, 27 AllDifferent units (doc §2, §7) | CSP: n² cells, row/column AllDifferent (doc §2, §7) | one search problem per sub-problem (doc §2 of each) |
| Representation (variables, domains, …) | `x[t][k][s]` ∈ {0..n−1}, canonical form, bitmasks (doc §3–§6) | cells ∈ {1..9}, row/column/box bitmasks (doc §3–§6) | cells ∈ {1..n}, row/column bitmasks, reduced form (doc §3–§6) | board tuple / `(m, c, boat)` / partial schedule (doc §3–§6) |
| Objective function | f(S) = longest valid prefix, V(S) repeated pairs (`objective.py`) | Φ(x) = V(x) + E(x) (`objective.py`) | Φ(x) = V(x) + E(x) (`objective.py`) | path to the goal; shortest path with BFS; feasibility for scheduling (doc §8) |
| Landscape | theoretical counts (`landscape.py`) + measured statistics (doc §9) | theoretical bounds + measured per difficulty (doc §9) | theoretical counts, literature L(n)/R(n), nodes per depth limit (doc §9) | state-space sizes + measured tree statistics (doc §9) |
| Required algorithm | DFS + backtracking (`solver.py`) | BFS (FIFO `deque`) + backtracking (`solver.py`) | IDDFS + backtracking (`solver.py`) | explicit search tree (`core.py`) |
| Problem-specific | configurable g, p, n, w; limits | Easy / Medium / Hard, classified by measured effort | configurable n; n = 3, 4, 5 tested | trees, parent-child links, duplicates, depth-limited Mermaid/text views |

Additional requirements from the project brief that were checked:

| Requirement | Evidence |
|---|---|
| Genuine BFS, not DFS labelled BFS | `test_bfs_expands_states_in_fifo_level_order` records the depth of every expanded state: non-decreasing, each level complete before the next |
| Genuine IDDFS | limits 0, 1, 2, … D (`test_depth_limits_start_at_zero_and_grow_by_one`); each iteration restarts from the root and never exceeds its limit (`test_each_iteration_respects_its_depth_limit`, `test_iterations_restart_from_the_root`) |
| Genuine DFS with backtracking | explicit undo of slot, week mask and pair bits; exhaustive counts equal known combinatorics (6 / 720 schedules, 1 / 2 canonical) |
| Independent validators | one per problem, sharing no code with the solvers; every CLI run validates its result |
| No external solvers or black boxes | the implementation imports only the Python standard library (checked by an import scan) |
| Workforce assumptions documented | [workforce_scheduling.md §0](workforce_scheduling.md) separates the official requirement from assumed rules R1–R6 |
| English-only documentation | all docs, comments, CLI messages and reports are in English (scan for Albanian text found only the file name `Detyra1.md`) |

## 3. Algorithms

| Problem | Algorithm and key techniques |
|---|---|
| Social Golfers | DFS with backtracking over canonical set partitions; bitmask pair checks; group and week forward checking; sound symmetry breaking (fixed week 1, ordered weeks); node/time limits; keeps the deepest feasible schedule |
| Sudoku | BFS over a FIFO queue, one cell per level (MRV or row-major); conflicts rejected and dead ends discarded (backtracking), search resumes from the next queued state; visited set; parent links rebuild the path |
| Latin Square | IDDFS: depth-limited DFS for limits 0..D; early rejection and explicit undo; stops when an iteration exhausts its tree without a cutoff; optional reduced form and depth step |
| Search Trees | explicit tree with BFS (FIFO) or DFS (LIFO); duplicate detection (graph search) or tree search with a depth limit; invalid transitions recorded as leaves; depth-limited text and Mermaid renderings |

## 4. Files

Created across the five phases (all files of the repository except the
initial `.gitignore` and `README.md`):

* `main.py`, `requirements.txt`, `pytest.ini`
* `social_golfers/`: `__init__.py`, `__main__.py`, `cli.py`, `landscape.py`, `model.py`, `objective.py`, `report.py`, `solver.py`, `validator.py`
* `sudoku/`: `__init__.py`, `__main__.py`, `cli.py`, `landscape.py`, `model.py`, `objective.py`, `puzzles.py`, `report.py`, `solver.py`, `validator.py`
* `latin_square/`: `__init__.py`, `__main__.py`, `cli.py`, `landscape.py`, `model.py`, `objective.py`, `report.py`, `solver.py`, `validator.py`
* `search_trees/`: `__init__.py`, `cli.py`, `core.py`, `report.py`, `visualization.py`, `eight_puzzle/{__init__,model,validator}.py`, `missionaries_cannibals/{__init__,model,validator}.py`, `workforce_scheduling/{__init__,model,validator}.py`
* `tests/`: `test_social_golfers.py`, `test_sudoku.py`, `test_latin_square.py`, `test_search_tree_core.py`, `test_eight_puzzle.py`, `test_missionaries_cannibals.py`, `test_workforce_scheduling.py`
* `docs/`: `social_golfers.md`, `sudoku.md`, `latin_square.md`, `search_trees.md`, `eight_puzzle.md`, `missionaries_cannibals.md`, `workforce_scheduling.md`, `final_report.md`

Modified: `README.md` (rewritten as the project README).

Changes made during the final verification (Phase 5):

* docstrings added to 20 public classes that had none;
* two unused helper functions removed (`sudoku.model.count_clues`,
  `RotatingWorkforce.index_of`);
* README: per-problem run sections, a Dependencies section, real example
  outputs, a link to this report, and a complete puzzle string in place of a
  shortened one that would have been rejected as invalid;
* `docs/sudoku.md` and `docs/latin_square.md`: outdated project-wide test
  totals replaced by a link to this report;
* `docs/final_report.md` (this file).

## 5. Test Results

Command: `python -m pytest`. Result: **315 tests collected, 315 passed,
0 failed, 50.8 s.**

| Test file | Tests | Passed |
|---|---|---|
| `tests/test_social_golfers.py` | 68 | 68 |
| `tests/test_sudoku.py` | 62 | 62 |
| `tests/test_latin_square.py` | 80 | 80 |
| `tests/test_search_tree_core.py` | 20 | 20 |
| `tests/test_eight_puzzle.py` | 32 | 32 |
| `tests/test_missionaries_cannibals.py` | 23 | 23 |
| `tests/test_workforce_scheduling.py` | 30 | 30 |
| **Total** | **315** | **315** |

Slowest tests: Latin square full grid n = 5 with step 5 (10.1 s), the
exhaustive 12-golfer optimality proof (9.5 s), reduced Latin square n = 6
(9.3 s), and exhaustion of all 181,440 boards of an unsolvable 8-Puzzle (5.9 s).

## 6. Verification of Reported Metrics

A verification script recomputed every deterministic headline number quoted
in the documentation and compared it with the documented value:
**33 metrics checked, 33 match, 0 mismatch.**

| Problem | Metrics re-checked |
|---|---|
| Social Golfers | 9-3-3: 4 weeks / 27 states; 16-4-4: 5 / 64; 12-4-3: 4 weeks proven / 906,200 states; 6-3-2: 2 canonical / 186 states and 720 / 10,512 without symmetry breaking; 4-2-2: 6 schedules; 32-8-4: 5 weeks / 1,999,880 backtracks at 2,000,000 states |
| Sudoku | Easy 51 / 0 / 1, Medium 100 / 3 / 4, Hard 17,136 / 1,799 / 826 (states / backtracks / max queue); 17-clue puzzle 2,356 states; Hard row-major 517,786 states / queue 61,667; deep unsolvable puzzle 3,851 states; Hard landscape (60 empty cells, 254 candidates, 0 singletons) |
| Latin Square | reduced n = 3..6: 19, 161, 4,914, 1,194,077 nodes; full n = 4: 24,861; full n = 5 step 5: 1,842,863; cutoffs 120 / 5,280 / 161,280 at limits 5 / 10 / 20; counts L(4) = 576, R(5) = 56, R(6) = 9,408 |
| Search Trees | 8-Puzzle default 5 moves / 54 nodes, full tree 181,440 states with maximum distance 31, hard instance 31 (BFS) vs 40,757 (DFS); M&C 11 crossings / 46 nodes, 15 reachable states, tree search 30,641 nodes / 4 goals, 4/4/2 unsolvable; workforce 82 (DFS) / 24,622 (BFS) nodes, 1,864 schedules, unsatisfiable variant 9,463 nodes |

Every generated solution in that script was also passed through the
problem's independent validator.

Elapsed times in the documents are single measurements on the development
machine and will differ elsewhere; they were not re-checked for equality.

## 7. Verification of Installation and Execution Instructions

* **Commands:** all 41 distinct `python main.py …` commands that appear in
  the README and the documentation were executed (placeholders such as
  `[--config file.json]` excluded; the files `my_puzzle.txt`, `puzzle.txt`
  and `my_rules.json` were created for the commands that read them). None
  crashed. All returned exit code 0 except the deliberate examples:
  `golfers -n 30` (2, n ≠ g × p), `sudoku --puzzle "55..."` (2, invalid
  puzzle), `latin -n 2 --prefill "1 ./. 2"` (1, no completion),
  `missionaries -m 4 -c 4 -b 2` (1, no solution). One README command used a
  shortened puzzle string and returned 2; it was replaced by the complete
  puzzle, which now solves.
* **Dependencies:** an import scan confirms that the implementation uses only
  the Python standard library; `pytest` is the only third-party package
  (tests only, listed in `requirements.txt`).
* **Not performed:** a fresh virtual environment with `pip install` was not
  created during verification (it would download packages); the project was
  tested with the already installed pytest 9.0.2. The code was run only on
  Python 3.13.1 on Windows. The README states Python 3.10+ because the code
  uses features introduced in 3.10 (`int.bit_count`, `dataclass(slots=True)`);
  older versions were not tested.

## 8. Code Quality Checks

A standard-library static check (no external linter installed) over all 50
Python files reports: no syntax errors, no unused imports, no non-standard
imports, no `TODO`/`FIXME` markers, module docstrings everywhere, docstrings
on all public classes. A reference scan found no unreferenced functions after
the two removals listed in Section 4.

Every package follows the same structure: model / solver (or engine) /
independent validator / objective / landscape / report / CLI, with algorithms,
problem representation, visualization and CLI kept in separate modules. The
search-tree package shares one engine across its three problems instead of
duplicating the search loop.

## 9. Documented Assumptions

* **Rotating Workforce Scheduling:** the assignment defines no constraints.
  Assumed: cyclic 3-employee × 7-day base schedule, shifts D/N/off, demand per
  day (R1), forbidden N→D (R2), at most 4 consecutive working days (R3), at most
  2 consecutive nights (R4), 3–5 working days per row (R5), availability (R6).
  All values are configurable through JSON.
* **Search Trees:** the assignment names no algorithm; BFS and DFS (the
  uninformed strategies of this assignment) are used.
* **Social Golfers:** `p ≥ 2` is required (with `p = 1` the number of weeks is
  unbounded).
* **Sudoku:** difficulty thresholds (Easy: no backtracking; Medium: ≤ 1,000
  expanded states; Hard: more) are a project rule applied to measured MRV-BFS
  statistics.
* **Latin Square:** the reduced form (first row and column fixed) is on by
  default as sound symmetry breaking; `--no-symmetry-breaking` searches the
  full grid. The pre-fill option is an extension beyond the assignment.

## 10. Known Limitations

* **Social Golfers:** for 32 golfers DFS finds 5 weeks within its limits; the
  known optimum is 10 weeks. The first 5-week prefix is a provable dead end
  and uninformed DFS thrashes in the week-5 subtree (20,000,000 states tried).
* **Sudoku:** BFS stores whole levels; with row-major ordering the Hard puzzle
  needs about 426 MiB and a 17-clue puzzle exceeds the default limits. All
  solutions lie on the last level, so stopping at the first solution saves
  little.
* **Latin Square:** goals exist only at the maximum depth, so every IDDFS
  iteration before the last is exhaustive. Practical range: n ≤ 6 (reduced
  form), n ≤ 5 (full grid); n = 7 does not finish within 60 s.
* **Search Trees:** uninformed BFS/DFS only (no heuristics); DFS paths can be
  far from optimal (40,757 moves on the hardest 8-Puzzle); drawings are always
  partial views; the workforce rules are assumptions.

## 11. Remaining Issues

No failing tests and no known defects. Open points that are limitations
rather than defects are listed in Section 10; the unverified installation
aspects are listed in Section 7.
