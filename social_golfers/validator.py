"""Independent validator for Social Golfers schedules.

It deliberately shares no code with the solver: it uses plain sets and a
``Counter`` of pairs instead of the solver's bitmasks, and it checks every
week, group, golfer and pair from scratch.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

from .model import GolferConfig


@dataclass
class ValidationReport:
    """Outcome of validating a schedule."""

    errors: list[str] = field(default_factory=list)
    weeks_checked: int = 0
    groups_checked: int = 0
    pairs_checked: int = 0
    repeated_pairs: dict[tuple[int, int], int] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def pair_meeting_counts(schedule: object) -> Counter[tuple[int, int]]:
    """Count in how many weeks each pair ``(a, b)``, ``a < b``, shares a group.

    Malformed entries (non-lists, non-integers) are ignored here; the
    validator reports them separately.
    """
    counts: Counter[tuple[int, int]] = Counter()
    if not isinstance(schedule, (list, tuple)):
        return counts
    for week in schedule:
        if not isinstance(week, (list, tuple)):
            continue
        for group in week:
            if not isinstance(group, (list, tuple)):
                continue
            members = sorted(
                {x for x in group if isinstance(x, int) and not isinstance(x, bool)}
            )
            counts.update(combinations(members, 2))
    return counts


def validate_schedule(
    schedule: object, config: GolferConfig, expected_weeks: int | None = None
) -> ValidationReport:
    """Check constraints C1-C5 for every week, group, golfer and pair."""
    report = ValidationReport()
    n, g, p = config.num_golfers, config.groups, config.group_size

    if not isinstance(schedule, (list, tuple)):
        report.errors.append("Schedule must be a list of weeks")
        return report
    if expected_weeks is not None and len(schedule) != expected_weeks:
        report.errors.append(
            f"Schedule has {len(schedule)} weeks, expected {expected_weeks}"
        )

    for w, week in enumerate(schedule, start=1):
        report.weeks_checked += 1
        if not isinstance(week, (list, tuple)):
            report.errors.append(f"Week {w} must be a list of groups")
            continue
        if len(week) != g:  # C3
            report.errors.append(f"Week {w} has {len(week)} groups, expected {g}")
        appearances: Counter[int] = Counter()
        for k, group in enumerate(week, start=1):
            report.groups_checked += 1
            if not isinstance(group, (list, tuple)):
                report.errors.append(f"Week {w}, group {k} must be a list of golfers")
                continue
            if len(group) != p:  # C2
                report.errors.append(
                    f"Week {w}, group {k} has {len(group)} golfers, expected {p}"
                )
            for golfer in group:
                if isinstance(golfer, bool) or not isinstance(golfer, int):
                    report.errors.append(
                        f"Week {w}, group {k}: golfer id {golfer!r} is not an integer"
                    )
                elif not 0 <= golfer < n:
                    report.errors.append(
                        f"Week {w}, group {k}: golfer {golfer} outside 0..{n - 1}"
                    )
                else:
                    appearances[golfer] += 1
        # C1: every golfer exactly once in the week.
        for golfer in range(n):
            if appearances[golfer] == 0:
                report.errors.append(f"Week {w}: golfer {golfer} is missing")
            elif appearances[golfer] > 1:
                report.errors.append(
                    f"Week {w}: golfer {golfer} appears {appearances[golfer]} times"
                )

    # C4: no pair together more than once.
    counts = pair_meeting_counts(schedule)
    report.pairs_checked = sum(counts.values())
    for (a, b), times in sorted(counts.items()):
        if times > 1:
            report.repeated_pairs[(a, b)] = times
            report.errors.append(f"Golfers {a} and {b} play together {times} times")
    return report
