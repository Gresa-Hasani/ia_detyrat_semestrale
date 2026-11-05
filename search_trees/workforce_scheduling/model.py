"""Rotating Workforce Scheduling (RWS) as a search problem.

The assignment only asks to "construct a search tree" for this problem; it
does not define its constraints. Everything below except the general idea of
a rotating (cyclic) schedule is an ASSUMPTION of this project, chosen to keep
the example small, adjustable and checkable. See docs/workforce_scheduling.md.

Model (assumed)
---------------
* A cyclic base schedule with ``employees`` rows (weeks) and ``days`` columns.
  Cell ``(w, d)`` holds a shift: one of the working shifts (default ``D`` =
  day, ``N`` = night) or ``-`` (day off).
* Rotation: employee ``e`` works row ``(e + k) mod employees`` in week ``k``.
  After the last day of row ``w`` an employee continues with the first day of
  row ``w + 1`` (and after the last row with row 0), so the schedule is read
  as one cyclic sequence of ``employees * days`` days.
* Constraints:
    R1 demand: on day ``d`` exactly ``demand[s][d]`` rows work shift ``s``;
    R2 forbidden sequences: e.g. ``N`` immediately followed by ``D``
       (insufficient rest), checked cyclically;
    R3 at most ``max_consecutive_work`` working days in a row (cyclic);
    R4 at most ``max_consecutive_same[s]`` consecutive days of shift ``s``;
    R5 workload distribution: every row has between ``min_work_per_row``
       and ``max_work_per_row`` working days;
    R6 availability: ``unavailable`` lists ``(employee, absolute_day)`` pairs
       (absolute day = ``week * days + day`` in the cycle) on which that
       employee must be off.

Search tree
-----------
The state is the tuple of shifts assigned so far, cells filled column by
column (day 1 for all rows, then day 2, ...), so the demand of a day is
complete as soon as its column is. A transition assigns one shift to the next
cell; it is *invalid* if it breaks a constraint that can already be checked,
and invalid nodes are never expanded. Depth ``employees * days`` is a goal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..core import SearchTreeError, Transition

OFF = "-"
State = tuple[str, ...]
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _int(name: str, value: object, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SearchTreeError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


@dataclass(frozen=True)
class WorkforceConfig:
    employees: int = 3
    days: int = 7
    shifts: tuple[str, ...] = ("D", "N")
    demand: dict[str, tuple[int, ...]] = field(default_factory=lambda: {
        "D": (1, 1, 1, 1, 1, 1, 1),
        "N": (1, 1, 1, 1, 1, 0, 0),
    })
    forbidden_sequences: tuple[tuple[str, str], ...] = (("N", "D"),)
    max_consecutive_work: int = 4
    max_consecutive_same: dict[str, int] = field(default_factory=lambda: {"N": 2})
    min_work_per_row: int = 3
    max_work_per_row: int = 5
    unavailable: tuple[tuple[int, int], ...] = ((0, 6),)   # employee 1 off on Sunday of week 1

    def __post_init__(self) -> None:
        _int("employees", self.employees, 1)
        _int("days", self.days, 1)
        if not self.shifts or len(set(self.shifts)) != len(self.shifts) or OFF in self.shifts:
            raise SearchTreeError(f"shifts must be distinct names other than {OFF!r}")
        if set(self.demand) != set(self.shifts):
            raise SearchTreeError("demand must define exactly one row per shift")
        for shift, row in self.demand.items():
            if len(row) != self.days or any(_int(f"demand[{shift}]", v, 0) is None for v in row):
                raise SearchTreeError(f"demand[{shift}] must list {self.days} non-negative integers")
        for d in range(self.days):
            if sum(self.demand[s][d] for s in self.shifts) > self.employees:
                raise SearchTreeError(f"demand on day {d + 1} exceeds the number of employees")
        for a, b in self.forbidden_sequences:
            if a not in self.shifts + (OFF,) or b not in self.shifts + (OFF,):
                raise SearchTreeError(f"forbidden sequence ({a}, {b}) uses an unknown shift")
        _int("max_consecutive_work", self.max_consecutive_work, 1)
        for shift, limit in self.max_consecutive_same.items():
            if shift not in self.shifts:
                raise SearchTreeError(f"max_consecutive_same uses unknown shift {shift!r}")
            _int(f"max_consecutive_same[{shift}]", limit, 1)
        _int("min_work_per_row", self.min_work_per_row, 0)
        _int("max_work_per_row", self.max_work_per_row, self.min_work_per_row)
        if self.max_work_per_row > self.days:
            raise SearchTreeError("max_work_per_row cannot exceed days")
        for e, t in self.unavailable:
            if not (0 <= _int("unavailable employee", e, 0) < self.employees
                    and 0 <= _int("unavailable day", t, 0) < self.employees * self.days):
                raise SearchTreeError(f"unavailable entry ({e}, {t}) is out of range")

    @property
    def cells(self) -> int:
        return self.employees * self.days

    def blocked_cells(self) -> set[tuple[int, int]]:
        """Base-schedule cells ``(row, day)`` that must be off because of R6."""
        blocked = set()
        for employee, absolute_day in self.unavailable:
            week, day = divmod(absolute_day, self.days)
            blocked.add(((employee + week) % self.employees, day))
        return blocked


def load_config(path: str | Path) -> WorkforceConfig:
    """Read a JSON configuration (keys as in ``WorkforceConfig``)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SearchTreeError(f"Cannot read configuration: {error}") from error
    if not isinstance(data, dict):
        raise SearchTreeError("Configuration must be a JSON object")
    try:
        return WorkforceConfig(
            employees=data.get("employees", 3),
            days=data.get("days", 7),
            shifts=tuple(data.get("shifts", ("D", "N"))),
            demand={k: tuple(v) for k, v in data["demand"].items()} if "demand" in data
            else WorkforceConfig().demand,
            forbidden_sequences=tuple(tuple(p) for p in data.get("forbidden_sequences", [("N", "D")])),
            max_consecutive_work=data.get("max_consecutive_work", 4),
            max_consecutive_same=dict(data.get("max_consecutive_same", {"N": 2})),
            min_work_per_row=data.get("min_work_per_row", 3),
            max_work_per_row=data.get("max_work_per_row", 5),
            unavailable=tuple(tuple(p) for p in data.get("unavailable", [(0, 6)])),
        )
    except (TypeError, AttributeError, ValueError) as error:
        if isinstance(error, SearchTreeError):
            raise
        raise SearchTreeError(f"Invalid configuration: {error}") from error


class RotatingWorkforce:
    """Search problem over partial base schedules (column-by-column filling)."""

    def __init__(self, config: WorkforceConfig | None = None) -> None:
        self.config = config or WorkforceConfig()
        cfg = self.config
        self.values = cfg.shifts + (OFF,)
        self.blocked = cfg.blocked_cells()
        self.forbidden = set(cfg.forbidden_sequences)

    # ------------------------------------------------------------ geometry
    def cell_of(self, index: int) -> tuple[int, int]:
        """Fill order position -> (row, day): column by column."""
        day, row = divmod(index, self.config.employees)
        return row, day

    def index_of(self, row: int, day: int) -> int:
        return day * self.config.employees + row

    def time_of(self, row: int, day: int) -> int:
        """Position in the cyclic sequence of days."""
        return row * self.config.days + day

    def cell_at_time(self, t: int) -> tuple[int, int]:
        return divmod(t % self.config.cells, self.config.days)

    # ------------------------------------------------------------- problem
    def initial_state(self) -> State:
        return ()

    def is_goal(self, state: State) -> bool:
        return len(state) == self.config.cells

    def expand(self, state: State) -> list[Transition[State]]:
        if len(state) >= self.config.cells:
            return []
        transitions = []
        row, day = self.cell_of(len(state))
        for value in self.values:
            reason = self.violation(state, row, day, value)
            action = f"r{row + 1} {DAY_NAMES[day % 7] if self.config.days == 7 else 'd' + str(day + 1)}={value}"
            transitions.append(Transition(action, state + (value,), valid=not reason, reason=reason))
        return transitions

    def violation(self, state: State, row: int, day: int, value: str) -> str:
        """First constraint broken by writing ``value`` in ``(row, day)``; '' if none."""
        cfg = self.config
        grid = self._grid(state)
        grid[(row, day)] = value
        working = value != OFF

        if working and (row, day) in self.blocked:                         # R6
            return "R6 availability: employee must be off"
        column = [grid.get((w, day)) for w in range(cfg.employees)]       # R1
        if working and column.count(value) > cfg.demand[value][day]:
            return f"R1 demand: more than {cfg.demand[value][day]} {value} on day {day + 1}"
        if not working and column.count(OFF) > cfg.employees - sum(cfg.demand[s][day] for s in cfg.shifts):
            return f"R1 demand: day {day + 1} would be understaffed"
        t = self.time_of(row, day)                                         # R2
        prev = grid.get(self.cell_at_time(t - 1))
        nxt = grid.get(self.cell_at_time(t + 1))
        if cfg.cells > 1 and prev is not None and (prev, value) in self.forbidden:
            return f"R2 forbidden sequence {prev}->{value}"
        if cfg.cells > 1 and nxt is not None and (value, nxt) in self.forbidden:
            return f"R2 forbidden sequence {value}->{nxt}"
        if working:                                                        # R3, R4
            if self._run(grid, t, lambda v: v != OFF) > cfg.max_consecutive_work:
                return f"R3 more than {cfg.max_consecutive_work} consecutive working days"
            limit = cfg.max_consecutive_same.get(value)
            if limit is not None and self._run(grid, t, lambda v: v == value) > limit:
                return f"R4 more than {limit} consecutive {value} shifts"
        row_values = [grid.get((row, d)) for d in range(cfg.days)]         # R5
        work = sum(1 for v in row_values if v not in (None, OFF))
        unknown = sum(1 for v in row_values if v is None)
        if work > cfg.max_work_per_row:
            return f"R5 row {row + 1} has more than {cfg.max_work_per_row} working days"
        if work + unknown < cfg.min_work_per_row:
            return f"R5 row {row + 1} cannot reach {cfg.min_work_per_row} working days"
        return ""

    def _grid(self, state: State) -> dict[tuple[int, int], str]:
        return {self.cell_of(i): v for i, v in enumerate(state)}

    def _run(self, grid: dict, t: int, predicate) -> int:
        """Length of the run of assigned cells satisfying ``predicate`` through time ``t``."""
        total, cells = 1, self.config.cells
        for direction in (-1, 1):
            k = 1
            while k < cells:
                v = grid.get(self.cell_at_time(t + direction * k))
                if v is None or not predicate(v):
                    break
                total += 1
                k += 1
            if total >= cells:
                return cells
        return total

    # ----------------------------------------------------------- rendering
    def schedule_rows(self, state: State) -> list[list[str]]:
        grid = self._grid(state)
        return [[grid.get((w, d), "?") for d in range(self.config.days)]
                for w in range(self.config.employees)]

    def format_state(self, state: State) -> str:
        return " | ".join("".join(row) for row in self.schedule_rows(state))

    def format_label(self, state: State) -> str:
        return "<br/>".join(" ".join(row) for row in self.schedule_rows(state))

    def format_schedule(self, state: State) -> str:
        cfg = self.config
        names = DAY_NAMES if cfg.days == 7 else tuple(f"d{d + 1}" for d in range(cfg.days))
        lines = ["Row   " + " ".join(f"{n:>3}" for n in names)]
        for w, row in enumerate(self.schedule_rows(state)):
            lines.append(f"R{w + 1:<4} " + " ".join(f"{v:>3}" for v in row))
        return "\n".join(lines)

    def employee_view(self, state: State) -> str:
        """What each employee works, week by week, following the rotation."""
        rows = self.schedule_rows(state)
        n = self.config.employees
        lines = []
        for e in range(n):
            weeks = ["".join(rows[(e + k) % n]) for k in range(n)]
            lines.append(f"Employee {e + 1}: " + " | ".join(weeks))
        return "\n".join(lines)
