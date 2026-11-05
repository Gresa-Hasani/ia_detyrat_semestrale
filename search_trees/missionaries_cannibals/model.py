"""Missionaries and Cannibals as a search problem.

* State: ``(m, c, b)`` = missionaries and cannibals on the LEFT bank and the
  boat side (``1`` = left, ``0`` = right). The right bank holds
  ``(M - m, C - c)``.
* Initial state: ``(M, C, 1)``; goal state: ``(0, 0, 0)``.
* Actions: the boat carries ``(dm, dc)`` people with
  ``1 <= dm + dc <= capacity``, from the bank where the boat is.
* Constraints:
    0 <= m <= M, 0 <= c <= C                     (cannot move people who are not there)
    m == 0 or m >= c                             (left bank safe)
    (M - m) == 0 or (M - m) >= (C - c)           (right bank safe)
  Missionaries may be outnumbered only on a bank with no missionaries.
  A crossing that produces an unsafe state is an *invalid transition*; it is
  recorded in the search tree but never expanded.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import SearchTreeError, Transition

State = tuple[int, int, int]


def _require(name: str, value: object, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SearchTreeError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


@dataclass(frozen=True)
class MissionariesCannibals:
    """Search problem with M missionaries, C cannibals and a boat of the given capacity."""

    missionaries: int = 3
    cannibals: int = 3
    capacity: int = 2

    def __post_init__(self) -> None:
        _require("missionaries", self.missionaries, 0)
        _require("cannibals", self.cannibals, 0)
        _require("boat capacity", self.capacity, 1)
        if self.missionaries + self.cannibals == 0:
            raise SearchTreeError("At least one person is required")
        if not self.is_safe((self.missionaries, self.cannibals, 1)):
            raise SearchTreeError("Initial state is unsafe: cannibals outnumber missionaries")

    # ------------------------------------------------------------ states
    def initial_state(self) -> State:
        return (self.missionaries, self.cannibals, 1)

    def goal_state(self) -> State:
        return (0, 0, 0)

    def is_goal(self, state: State) -> bool:
        return state == self.goal_state()

    def in_range(self, state: State) -> bool:
        m, c, b = state
        return 0 <= m <= self.missionaries and 0 <= c <= self.cannibals and b in (0, 1)

    def is_safe(self, state: State) -> bool:
        m, c, _ = state
        right_m, right_c = self.missionaries - m, self.cannibals - c
        return (m == 0 or m >= c) and (right_m == 0 or right_m >= right_c)

    # ------------------------------------------------------- transitions
    def boat_loads(self) -> list[tuple[int, int]]:
        """All loads (dm, dc) with 1 <= dm + dc <= capacity, in a fixed order."""
        return [(dm, dc) for dm in range(self.capacity + 1) for dc in range(self.capacity + 1 - dm)
                if dm + dc >= 1]

    def expand(self, state: State) -> list[Transition[State]]:
        m, c, b = state
        sign = -1 if b == 1 else 1          # boat on the left takes people away from it
        side = "R" if b == 1 else "L"       # bank the boat travels to
        result = []
        for dm, dc in self.boat_loads():
            action = f"{dm}M{dc}C to {side}"
            nxt = (m + sign * dm, c + sign * dc, 1 - b)
            if not self.in_range(nxt):
                continue                     # not enough people on the boat's bank: not applicable
            if not self.is_safe(nxt):
                result.append(Transition(action, nxt, valid=False, reason=self.unsafe_reason(nxt)))
            else:
                result.append(Transition(action, nxt))
        return result

    def unsafe_reason(self, state: State) -> str:
        m, c, _ = state
        rm, rc = self.missionaries - m, self.cannibals - c
        if m and c > m:
            return f"left bank: {c} cannibals > {m} missionaries"
        return f"right bank: {rc} cannibals > {rm} missionaries"

    # --------------------------------------------------------- rendering
    def format_state(self, state: State) -> str:
        m, c, b = state
        rm, rc = self.missionaries - m, self.cannibals - c
        boat = "[boat] ~~~      " if b == 1 else "      ~~~ [boat]"
        return f"({m},{c},{'L' if b else 'R'}) {m}M{c}C {boat} {rm}M{rc}C"

    def format_label(self, state: State) -> str:
        m, c, b = state
        return f"({m},{c},{'L' if b else 'R'})<br/>L: {m}M {c}C | R: {self.missionaries - m}M {self.cannibals - c}C"

    def all_states(self) -> list[State]:
        return [(m, c, b) for m in range(self.missionaries + 1) for c in range(self.cannibals + 1)
                for b in (1, 0)]
