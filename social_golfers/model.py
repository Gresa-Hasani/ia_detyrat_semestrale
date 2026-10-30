"""CSP model of the Social Golfers Problem (SGP).

Problem: schedule ``n = g * p`` golfers into ``g`` groups of ``p`` golfers for
``w`` weeks so that no two golfers play in the same group more than once.

CSP formulation used throughout this package
--------------------------------------------
* Variables: ``x[w][k][s]`` = the golfer placed in slot ``s`` of group ``k``
  in week ``w`` (``0 <= w < W``, ``0 <= k < g``, ``0 <= s < p``).
* Domains:   ``D(x[w][k][s]) = {0, 1, ..., n - 1}``.
* Constraints:
    C1  every golfer appears exactly once in every week;
    C2  every group contains exactly ``p`` golfers;
    C3  every week contains exactly ``g`` groups;
    C4  every pair of golfers shares a group in at most one week;
    C5  every produced week satisfies C1-C4.

A week is a *set partition* of the golfers, so the solver stores each week in
canonical form (golfers ascending inside a group, groups ordered by their
smallest golfer). This removes representation duplicates without losing any
solution.
"""

from __future__ import annotations

from dataclasses import dataclass

# A schedule is a list of weeks; a week is a list of groups; a group is a list
# of golfer ids in the range 0..n-1.
Schedule = list[list[list[int]]]


class ConfigurationError(ValueError):
    """Raised when problem or search parameters are invalid."""


def require_int(name: str, value: object, minimum: int) -> int:
    """Return ``value`` if it is an int ``>= minimum``; raise otherwise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}")
    if value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass(frozen=True)
class GolferConfig:
    """Parameters ``g`` (groups per week) and ``p`` (golfers per group).

    ``p >= 2`` is required: with ``p = 1`` no two golfers ever share a group,
    the pair constraint is empty and the number of weeks is unbounded.
    """

    groups: int
    group_size: int

    def __post_init__(self) -> None:
        require_int("groups (g)", self.groups, 1)
        require_int("group size (p)", self.group_size, 2)

    @classmethod
    def from_parameters(
        cls, groups: int, group_size: int, golfers: int | None = None
    ) -> "GolferConfig":
        """Build a config and, if ``golfers`` is given, check ``n == g * p``."""
        config = cls(groups, group_size)
        if golfers is not None:
            require_int("number of golfers (n)", golfers, 2)
            if golfers != config.num_golfers:
                raise ConfigurationError(
                    f"n must equal g x p: n={golfers}, but g x p = "
                    f"{groups} x {group_size} = {config.num_golfers}"
                )
        return config

    @property
    def num_golfers(self) -> int:
        """``n = g * p``."""
        return self.groups * self.group_size

    @property
    def week_upper_bound(self) -> int:
        """Theoretical upper bound on the number of weeks.

        * Pigeonhole: in week 2 each group needs ``p`` golfers taken from
          ``p`` *different* week-1 groups, so ``p > g`` forces ``W <= 1``.
        * Counting: every week a golfer meets ``p - 1`` new partners out of
          ``n - 1`` possible ones, so ``W <= floor((n - 1) / (p - 1))``.
        """
        if self.group_size > self.groups:
            return 1
        return (self.num_golfers - 1) // (self.group_size - 1)
