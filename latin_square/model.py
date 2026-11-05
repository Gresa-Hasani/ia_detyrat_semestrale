"""CSP model of the Latin Square problem.

* Variables: the ``n * n`` cells ``x[r][c]``.
* Domains:   ``D(x[r][c]) = {1, ..., n}``.
* Constraints: ``AllDifferent`` on every row and every column
  (each value appears exactly once per row and per column).

A grid is a tuple of rows; each row is a tuple of ints, ``0`` = empty.
An optional pre-filled grid (Latin square *completion*) is supported as an
extension; the assignment itself starts from the empty grid.
"""

from __future__ import annotations

Grid = tuple[tuple[int, ...], ...]


class LatinSquareError(ValueError):
    """Raised for invalid sizes, malformed grids or contradictory pre-fills."""


def require_size(n: object) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise LatinSquareError(f"n must be an integer, got {n!r}")
    if n < 1:
        raise LatinSquareError(f"n must be >= 1, got {n}")
    return n


def empty_grid(n: int) -> Grid:
    require_size(n)
    return tuple((0,) * n for _ in range(n))


def parse_grid(text: str, n: int) -> Grid:
    """Parse rows separated by ``/`` (or new lines) and cells separated by
    spaces or commas; ``.`` or ``0`` mean empty. Example for n = 3:
    ``"1 . ./. . 1/. . ."``.
    """
    require_size(n)
    if not isinstance(text, str):
        raise LatinSquareError("Grid must be given as a string")
    rows_text = [r for r in text.replace("\n", "/").split("/") if r.strip()]
    if len(rows_text) != n:
        raise LatinSquareError(f"Grid must have {n} rows, got {len(rows_text)}")
    rows = []
    for r, row_text in enumerate(rows_text, start=1):
        tokens = row_text.replace(",", " ").split()
        if len(tokens) != n:
            raise LatinSquareError(f"Row {r} must have {n} cells, got {len(tokens)}")
        row = []
        for token in tokens:
            if token == ".":
                row.append(0)
            elif token.isdigit():
                row.append(int(token))
            else:
                raise LatinSquareError(f"Invalid cell value {token!r} in row {r}")
        rows.append(tuple(row))
    return check_grid(tuple(rows), n)


def find_conflicts(grid: Grid) -> list[str]:
    """Describe every repeated value in a row or column (empty cells ignored)."""
    conflicts = []
    n = len(grid)
    for r in range(n):
        seen: dict[int, int] = {}
        for c in range(n):
            v = grid[r][c]
            if v and v in seen:
                conflicts.append(f"value {v} repeated in row {r + 1} (columns {seen[v] + 1} and {c + 1})")
            elif v:
                seen[v] = c
    for c in range(n):
        seen = {}
        for r in range(n):
            v = grid[r][c]
            if v and v in seen:
                conflicts.append(f"value {v} repeated in column {c + 1} (rows {seen[v] + 1} and {r + 1})")
            elif v:
                seen[v] = r
    return conflicts


def check_grid(grid: object, n: int) -> Grid:
    """Validate shape, value range (0..n) and absence of conflicts."""
    require_size(n)
    if not isinstance(grid, tuple) or len(grid) != n:
        raise LatinSquareError(f"Grid must be a tuple of {n} rows")
    for r, row in enumerate(grid, start=1):
        if not isinstance(row, tuple) or len(row) != n:
            raise LatinSquareError(f"Row {r} must be a tuple of {n} cells")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= n:
                raise LatinSquareError(f"Cell values must be integers 0..{n}, got {value!r} in row {r}")
    conflicts = find_conflicts(grid)
    if conflicts:
        raise LatinSquareError("Invalid pre-filled grid: " + "; ".join(conflicts))
    return grid


def reduced_prefill(n: int) -> Grid:
    """First row and first column fixed to 1..n (reduced / normalised form)."""
    require_size(n)
    return tuple(
        tuple((c + 1) if r == 0 else (r + 1) if c == 0 else 0 for c in range(n))
        for r in range(n)
    )


def format_grid(grid: Grid) -> str:
    width = len(str(len(grid)))
    return "\n".join(
        " ".join(str(v).rjust(width) if v else ".".rjust(width) for v in row) for row in grid
    )
