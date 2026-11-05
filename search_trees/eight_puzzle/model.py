"""8-Puzzle as a search problem.

* State: a tuple of 9 integers, the 3x3 board read row by row; ``0`` is the
  empty tile (blank).
* Actions: move the blank Up, Down, Left or Right (equivalently, slide the
  neighbouring tile into the blank). A move that would leave the board is not
  applicable.
* Transition: swap the blank with the neighbouring tile.
* Goal: the configured goal board.

Solvability: a move never changes the parity of the number of inversions
(pairs of tiles out of order, blank ignored) on a 3-wide board, so a goal is
reachable exactly when initial and goal boards have the same inversion parity.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import SearchTreeError, Transition

Board = tuple[int, ...]
SIZE = 3

DEFAULT_GOAL: Board = (1, 2, 3, 8, 0, 4, 7, 6, 5)       # Nilsson's goal (blank in the centre)
DEFAULT_INITIAL: Board = (2, 8, 3, 1, 6, 4, 7, 0, 5)    # Nilsson's example, 5 moves from the goal
MOVES = (("Up", -1, 0), ("Down", 1, 0), ("Left", 0, -1), ("Right", 0, 1))


def parse_board(text: str) -> Board:
    """Parse 9 tiles separated by spaces, commas or '/' (0 or '_' = blank)."""
    if not isinstance(text, str):
        raise SearchTreeError("Board must be given as a string")
    tokens = text.replace("/", " ").replace(",", " ").split()
    tiles = []
    for token in tokens:
        if token in ("_", "."):
            tiles.append(0)
        elif token.isdigit():
            tiles.append(int(token))
        else:
            raise SearchTreeError(f"Invalid tile {token!r}")
    return check_board(tuple(tiles))


def check_board(board: object) -> Board:
    """A valid board is a permutation of 0..8."""
    if not isinstance(board, tuple) or len(board) != SIZE * SIZE:
        raise SearchTreeError(f"Board must have {SIZE * SIZE} tiles")
    if any(isinstance(t, bool) or not isinstance(t, int) for t in board):
        raise SearchTreeError("Tiles must be integers")
    if sorted(board) != list(range(SIZE * SIZE)):
        raise SearchTreeError(f"Board must contain each of 0..{SIZE * SIZE - 1} exactly once, got {board}")
    return board


def inversions(board: Board) -> int:
    tiles = [t for t in board if t]
    return sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])


def is_solvable(initial: Board, goal: Board) -> bool:
    return inversions(initial) % 2 == inversions(goal) % 2


def apply_move(board: Board, action: str) -> Board | None:
    """Board after moving the blank, or None if the move leaves the board."""
    blank = board.index(0)
    row, col = divmod(blank, SIZE)
    for name, dr, dc in MOVES:
        if name == action:
            r, c = row + dr, col + dc
            if not (0 <= r < SIZE and 0 <= c < SIZE):
                return None
            target = r * SIZE + c
            tiles = list(board)
            tiles[blank], tiles[target] = tiles[target], tiles[blank]
            return tuple(tiles)
    raise SearchTreeError(f"Unknown action {action!r}")


def format_board(board: Board) -> str:
    return " / ".join(" ".join(str(t) if t else "_" for t in board[r * SIZE:(r + 1) * SIZE])
                      for r in range(SIZE))


def board_label(board: Board) -> str:
    return "<br/>".join(" ".join(str(t) if t else "_" for t in board[r * SIZE:(r + 1) * SIZE])
                        for r in range(SIZE))


@dataclass(frozen=True)
class EightPuzzle:
    """Search problem; legal actions are the blank moves that stay on the board."""

    initial: Board = DEFAULT_INITIAL
    goal: Board = DEFAULT_GOAL

    def __post_init__(self) -> None:
        check_board(self.initial)
        check_board(self.goal)

    def initial_state(self) -> Board:
        return self.initial

    def is_goal(self, state: Board) -> bool:
        return state == self.goal

    def legal_actions(self, state: Board) -> list[str]:
        return [name for name, _, _ in MOVES if apply_move(state, name) is not None]

    def expand(self, state: Board) -> list[Transition[Board]]:
        # Off-board moves are not applicable actions, not states, so they are
        # simply not generated.
        return [Transition(action, apply_move(state, action)) for action in self.legal_actions(state)]

    def format_state(self, state: Board) -> str:
        return format_board(state)

    def format_label(self, state: Board) -> str:
        return board_label(state)

    @property
    def solvable(self) -> bool:
        return is_solvable(self.initial, self.goal)


# Theoretical state space: 9! boards, split into two parity classes.
TOTAL_BOARDS = 362_880
REACHABLE_BOARDS = TOTAL_BOARDS // 2      # 181,440
# Average branching factor over all blank positions: (4*2 + 4*3 + 1*4) / 9.
AVERAGE_BRANCHING_FACTOR = (4 * 2 + 4 * 3 + 1 * 4) / 9


# ------------------------------------------------------------ diagram style
def _puzzle_view(board: Board):
    from ..graphics import NodeView
    rows = tuple(tuple(str(t) if t else "" for t in board[r * SIZE:(r + 1) * SIZE]) for r in range(SIZE))
    return NodeView("grid", rows, cell_styles={"": ("#38bdf8", "#000000")})


def _puzzle_caption(node) -> str:
    if node.status == "duplicate" and node.reason:
        return f"repeat of depth {node.reason.split()[-1]}"
    return ""


def diagram_style(title: str = "8-Puzzle search tree"):
    """Look of the graphical diagram: each node is the 3x3 board, blank in blue."""
    from ..graphics import DiagramStyle
    return DiagramStyle(
        title=title,
        view=_puzzle_view,
        caption=_puzzle_caption,
        notes=("Each node is a board; the blue cell is the blank.",
               "Edge label = direction in which the blank moves (Up, Down, Left, Right)."),
        cell_legend=(("#38bdf8", "#000000", "", "blank cell"),),
    )
