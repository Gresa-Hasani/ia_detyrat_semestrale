"""Objective function for the Social Golfers Problem.

Hard constraints C1-C4 decide *feasibility*; the objective measures *quality*:

    maximise  f(S) = |S|   (number of weeks)   subject to  S feasible.

For an arbitrary (possibly infeasible) schedule ``S = (W_1, ..., W_m)`` we use

    f(S) = max { k : (W_1, ..., W_k) satisfies C1-C4 }

i.e. the length of its longest valid prefix, together with the penalty

    V(S) = sum over pairs {a, b} of max(0, m_ab(S) - 1)

where ``m_ab(S)`` is the number of weeks in which ``a`` and ``b`` share a
group. ``V(S) = 0`` is necessary (not sufficient) for feasibility; the
structural constraints C1-C3 are checked by the validator.
"""

from __future__ import annotations

from .model import GolferConfig, Schedule
from .validator import pair_meeting_counts, validate_schedule


def repeated_pair_violations(schedule: Schedule) -> int:
    """Penalty ``V(S)``: the number of extra (repeated) pair meetings."""
    return sum(times - 1 for times in pair_meeting_counts(schedule).values() if times > 1)


def objective_value(schedule: Schedule, config: GolferConfig) -> int:
    """``f(S)``: number of leading weeks that form a feasible schedule."""
    best = 0
    for k in range(1, len(schedule) + 1):
        if not validate_schedule(schedule[:k], config).is_valid:
            break
        best = k
    return best
