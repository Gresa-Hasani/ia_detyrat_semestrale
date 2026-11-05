# ia_detyrat_semestrale

Artificial Intelligence 2026 — Assignment 1: Uninformed Search Techniques
([assignment text](https://github.com/adrianymeri/Artificial-Intelligence-2026/blob/main/Detyra1.md)).

| # | Problem | Required algorithm | Status |
|---|---|---|---|
| 1 | Social Golfers Problem | Depth First Search (DFS) with Backtracking | Implemented ([docs](docs/social_golfers.md)) |
| 2 | Sudoku Solver (Easy / Medium / Hard) | Breadth First Search (BFS) with Backtracking | Implemented ([docs](docs/sudoku.md)) |
| 3 | Latin Square | Iterative Deepening DFS (IDDFS) with Backtracking | Planned (Phase 3) |
| 4 | Search Trees: 8-Puzzle, Missionaries and Cannibals, Rotating Workforce Scheduling | Search-tree construction | Planned (Phase 4) |

All search algorithms are implemented by hand; no external solver libraries
are used.

## Technologies

* Python 3.10+ (developed and tested with Python 3.13.1)
* Standard library only for the implementation
* pytest for automated tests

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (use: source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
```

## Project Structure

```
main.py                      CLI entry point (one subcommand per problem)
social_golfers/              Problem 1
  model.py                   CSP configuration and theoretical bounds
  solver.py                  DFS with backtracking, pruning, statistics
  validator.py               independent schedule validator
  objective.py               objective function f(S) and penalty V(S)
  landscape.py               theoretical search-landscape formulas
  report.py                  text output (schedule table, statistics)
  cli.py                     command-line options
sudoku/                      Problem 2
  model.py                   grid parsing, units, initial validation
  solver.py                  BFS (FIFO queue) with backtracking, statistics
  validator.py               independent solution validator
  objective.py               objective function V(x) + E(x)
  landscape.py               theoretical search-landscape figures
  puzzles.py                 Easy / Medium / Hard puzzles, measured classification
  report.py, cli.py          text output and command-line options
tests/                       pytest test suites
docs/                        detailed documentation per problem
requirements.txt
pytest.ini
```

## Running

```bash
python main.py golfers --help
python main.py golfers -g 8 -p 4                        # 32 golfers, groups of 4
python main.py golfers -g 3 -p 3                        # 9 golfers, solved optimally (4 weeks)
python main.py golfers -g 8 -p 4 -w 5 --max-nodes 100000 --time-limit 30
python main.py golfers -g 3 -p 2 --count-solutions       # count all schedules
```

Options of `golfers`:

| Option | Meaning | Default |
|---|---|---|
| `-g`, `--groups` | groups per week | 8 |
| `-p`, `--size` | golfers per group | 4 |
| `-n`, `--golfers` | total golfers (must equal g × p) | g × p |
| `-w`, `--weeks` | target number of weeks | theoretical upper bound ⌊(n−1)/(p−1)⌋ |
| `--max-nodes` | limit on expanded states (0 = unlimited) | 2,000,000 |
| `--time-limit` | limit in seconds (0 = unlimited) | 60 |
| `--no-symmetry-breaking` | do not fix week 1 or order the weeks | off |
| `--count-solutions` | count all target-length schedules instead of stopping at the first | off |

The package can also be run directly: `python -m social_golfers -g 3 -p 3`.

Exit codes: `0` success, `1` independent validation failed, `2` invalid parameters.

```bash
python main.py sudoku --help
python main.py sudoku -d easy                           # or medium / hard
python main.py sudoku -d hard --show-path               # print the solution path
python main.py sudoku -d hard --order row-major         # compare variable orders
python main.py sudoku --puzzle "53..7....6..195..."      # custom 81-character puzzle
python main.py sudoku --file puzzle.txt --count-solutions
```

Options of `sudoku`:

| Option | Meaning | Default |
|---|---|---|
| `-d`, `--difficulty` | predefined puzzle: easy, medium, hard | easy |
| `--puzzle` / `--file` | custom puzzle (81 cells, `.` or `0` = empty) | — |
| `--order` | cell expanded by each state: `mrv` or `row-major` | mrv |
| `--count-solutions` | find all solutions instead of stopping at the first | off |
| `--max-states` | limit on expanded states (0 = unlimited) | 1,000,000 |
| `--max-queue` | limit on queue size (0 = unlimited) | 2,000,000 |
| `--time-limit` | seconds (0 = unlimited) | 60 |
| `--show-path` | print the assignments leading to the solution | off |

Exit codes: `0` solved and validated, `1` no solution / limit reached / validation failed, `2` invalid puzzle or parameters.

## Testing

```bash
python -m pytest            # all tests
python -m pytest -v tests/test_social_golfers.py
python -m pytest -v tests/test_sudoku.py
```

## Problem 1 — Social Golfers Problem

Schedule `n = g × p` golfers into `g` groups of `p` for as many weeks as
possible so that no two golfers share a group twice.

* **Model:** CSP with variables `x[t][k][s]` (golfer in slot `s` of group `k`
  in week `t`), domains `{0, …, n−1}`, hard constraints C1–C4 (one group per
  golfer per week, group size `p`, `g` groups per week, no repeated pair).
* **Objective:** maximise `f(S)`, the length of the longest valid prefix of the
  schedule; penalty `V(S)` counts repeated pair meetings.
* **Landscape:** theoretical counts (`n^(n·w)`, `(n!)^w`, partitions per week
  `n!/((p!)^g g!)`, canonical schedules `C(P−1, w−1)`) and measured statistics
  (expanded states, backtracks, rejections by reason, branching factors,
  validity ratio, depth).
* **Algorithm:** DFS with backtracking, bitmask constraint checks, group and
  week forward checking, sound symmetry breaking, node/time limits.
* **Validation:** an independent validator re-checks every week, group, golfer
  and pair.

Measured results (2,000,000-state limit):

| Instance | Upper bound | Weeks found | Proven optimal | States expanded |
|---|---|---|---|---|
| 9 golfers (3 × 3) | 4 | 4 | yes | 27 |
| 16 golfers (4 × 4) | 5 | 5 | yes | 64 |
| 12 golfers (4 × 3) | 5 | 4 | yes (exhaustive) | 906,200 |
| 32 golfers (8 × 4) | 10 | 5 | no (limit reached) | 2,000,000 |

Full documentation: [docs/social_golfers.md](docs/social_golfers.md).

## Problem 2 — Sudoku Solver

* **Model:** CSP with 81 variables (cells), domains `{1..9}` (clues fixed),
  27 `AllDifferent` constraints (rows, columns, boxes). Invalid puzzles are
  rejected with a message naming the repeated digit and unit.
* **Objective:** minimise `Φ(x) = V(x) + E(x)`: constraint violations plus
  empty cells; `Φ = 0` exactly for a solution.
* **Landscape:** theoretical bounds (`9^E`, initial domain product, candidate
  counts) and measured statistics (expanded/generated states, invalid partial
  states, dead ends, queue size per level, branching factors).
* **Algorithm:** genuine BFS over a FIFO `deque`; every state fills one cell
  (MRV or row-major); conflicting digits and dead ends (forward check) are
  discarded and the search resumes from the next queued alternative
  (backtracking); parent links rebuild the solution path.
* **Difficulty:** assigned from measured MRV-BFS effort, not clue count.

Measured results (MRV ordering, default limits):

| Puzzle | Clues | States expanded | Backtracks | Max queue | Measured difficulty |
|---|---|---|---|---|---|
| Easy | 30 | 51 | 0 | 1 | easy |
| Medium | 27 | 100 | 3 | 4 | medium |
| Hard | 21 | 17,136 | 1,799 | 826 | hard |

Full documentation: [docs/sudoku.md](docs/sudoku.md).

## Known Limitations

* Social Golfers: for 32 golfers, uninformed DFS finds 5 weeks; the known
  optimum of 10 weeks is out of reach without heuristics or algebraic
  constructions (see Section 16 of the documentation).
* Sudoku: BFS keeps a whole level of the search tree in memory; with
  row-major ordering the Hard puzzle needs about 426 MiB, and the 17-clue
  extra puzzle exceeds the default limits.
