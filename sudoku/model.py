"""CSP model of 9x9 Sudoku.

* Variables: the 81 cells ``X_i``, ``i = 9 * row + col``.
* Domains:   ``D(X_i) = {1..9}`` for empty cells, ``{given}`` for clues.
* Constraints: ``AllDifferent`` on each of the 27 units
  (9 rows, 9 columns, 9 boxes of 3x3); clues cannot change.

A grid is stored as a tuple of 81 integers, ``0`` meaning "empty".
"""

from __future__ import annotations

Grid = tuple[int, ...]

SIZE = 9
BOX = 3
CELLS = SIZE * SIZE
DIGITS = range(1, SIZE + 1)
ALL_DIGITS_MASK = 0b1111111110  # bits 1..9 set


class SudokuError(ValueError):
    """Raised for malformed or contradictory puzzles and invalid parameters."""


def row_of(cell: int) -> int:
    return cell // SIZE


def col_of(cell: int) -> int:
    return cell % SIZE


def box_of(cell: int) -> int:
    return (row_of(cell) // BOX) * BOX + col_of(cell) // BOX


def _build_units() -> tuple[tuple[str, tuple[int, ...]], ...]:
    units = []
    for r in range(SIZE):
        units.append((f"row {r + 1}", tuple(r * SIZE + c for c in range(SIZE))))
    for c in range(SIZE):
        units.append((f"column {c + 1}", tuple(r * SIZE + c for r in range(SIZE))))
    for b in range(SIZE):
        top, left = (b // BOX) * BOX, (b % BOX) * BOX
        units.append((
            f"box {b + 1}",
            tuple((top + dr) * SIZE + left + dc for dr in range(BOX) for dc in range(BOX)),
        ))
    return tuple(units)


# The 27 units, each as (name, cell indices).
UNITS = _build_units()


def parse_grid(text: str) -> Grid:
    """Parse 81 cells from a string; ``.`` or ``0`` mean empty.

    Whitespace and the separators ``|``, ``-`` and ``+`` are ignored, so both a
    single 81-character line and a 9-line drawing are accepted.
    """
    if not isinstance(text, str):
        raise SudokuError("Puzzle must be given as a string")
    cells = []
    for ch in text:
        if ch.isspace() or ch in "|-+":
            continue
        if ch in ".0":
            cells.append(0)
        elif ch in "123456789":
            cells.append(int(ch))
        else:
            raise SudokuError(f"Invalid character {ch!r} in puzzle")
    if len(cells) != CELLS:
        raise SudokuError(f"Puzzle must have {CELLS} cells, got {len(cells)}")
    return tuple(cells)


def find_conflicts(grid: Grid) -> list[str]:
    """Describe every duplicate digit inside a unit (empty cells ignored)."""
    conflicts = []
    for name, cells in UNITS:
        seen: dict[int, int] = {}
        for cell in cells:
            digit = grid[cell]
            if digit == 0:
                continue
            if digit in seen:
                conflicts.append(
                    f"digit {digit} repeated in {name} "
                    f"(r{row_of(seen[digit]) + 1}c{col_of(seen[digit]) + 1} and "
                    f"r{row_of(cell) + 1}c{col_of(cell) + 1})"
                )
            else:
                seen[digit] = cell
    return conflicts


def check_puzzle(grid: Grid) -> Grid:
    """Validate the initial puzzle: 81 values in 0..9 and no conflicting clues."""
    if not isinstance(grid, tuple) or len(grid) != CELLS:
        raise SudokuError(f"Grid must be a tuple of {CELLS} cells")
    for value in grid:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
            raise SudokuError(f"Cell values must be integers 0..9, got {value!r}")
    conflicts = find_conflicts(grid)
    if conflicts:
        raise SudokuError("Invalid puzzle: " + "; ".join(conflicts))
    return grid


def format_grid(grid: Grid) -> str:
    """Render a grid as 9 text lines with box separators."""
    lines = []
    for r in range(SIZE):
        if r and r % BOX == 0:
            lines.append("------+-------+------")
        row = []
        for c in range(SIZE):
            if c and c % BOX == 0:
                row.append("|")
            value = grid[r * SIZE + c]
            row.append(str(value) if value else ".")
        lines.append(" ".join(row))
    return "\n".join(lines)
