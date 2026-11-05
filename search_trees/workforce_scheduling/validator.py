"""Independent validator for complete rotating workforce schedules.

It works on the plain base-schedule matrix (list of rows of shift names) and
re-derives every constraint from the configuration, without using the search
model's incremental checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

OFF = "-"


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _cyclic_runs(sequence: list[str], predicate) -> list[int]:
    """Lengths of maximal runs of elements satisfying ``predicate`` (cyclic)."""
    n = len(sequence)
    flags = [predicate(v) for v in sequence]
    if all(flags):
        return [n]
    start = flags.index(False)          # rotate so the sequence starts outside a run
    rotated = flags[start:] + flags[:start]
    runs, current = [], 0
    for flag in rotated:
        if flag:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def validate_schedule(rows: list[list[str]], config) -> ValidationReport:
    report = ValidationReport()
    n, days = config.employees, config.days
    allowed = set(config.shifts) | {OFF}
    if len(rows) != n or any(len(r) != days for r in rows):
        report.errors.append(f"Schedule must have {n} rows of {days} days")
        return report
    for w, row in enumerate(rows, start=1):
        for d, v in enumerate(row, start=1):
            if v not in allowed:
                report.errors.append(f"Row {w}, day {d}: unknown shift {v!r}")
    if report.errors:
        return report

    for d in range(days):                                           # R1
        for s in config.shifts:
            have = sum(1 for w in range(n) if rows[w][d] == s)
            if have != config.demand[s][d]:
                report.errors.append(f"Day {d + 1}: {have} x {s}, demand {config.demand[s][d]}")

    sequence = [v for row in rows for v in row]                     # cyclic order of days
    total = len(sequence)
    if total > 1:                                                   # R2
        for t in range(total):
            pair = (sequence[t], sequence[(t + 1) % total])
            if pair in set(map(tuple, config.forbidden_sequences)):
                report.errors.append(f"Forbidden sequence {pair[0]}->{pair[1]} at position {t + 1}")

    work_runs = _cyclic_runs(sequence, lambda v: v != OFF)          # R3
    if work_runs and max(work_runs) > config.max_consecutive_work:
        report.errors.append(f"Working run of {max(work_runs)} days (max {config.max_consecutive_work})")
    for shift, limit in config.max_consecutive_same.items():        # R4
        runs = _cyclic_runs(sequence, lambda v, s=shift: v == s)
        if runs and max(runs) > limit:
            report.errors.append(f"Run of {max(runs)} {shift} shifts (max {limit})")

    for w, row in enumerate(rows, start=1):                         # R5
        work = sum(1 for v in row if v != OFF)
        if not config.min_work_per_row <= work <= config.max_work_per_row:
            report.errors.append(
                f"Row {w} has {work} working days (allowed {config.min_work_per_row}..{config.max_work_per_row})"
            )

    for employee, absolute_day in config.unavailable:               # R6 via the rotation
        week, day = divmod(absolute_day, days)
        row = (employee + week) % n
        if rows[row][day] != OFF:
            report.errors.append(
                f"Employee {employee + 1} is unavailable on week {week + 1} day {day + 1} "
                f"but works {rows[row][day]}"
            )
    return report
