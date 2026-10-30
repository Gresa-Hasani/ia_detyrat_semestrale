"""Plain-text formatting of schedules, landscape figures and search results."""

from __future__ import annotations

from .landscape import TheoreticalLandscape
from .model import Schedule
from .solver import SearchResult
from .validator import ValidationReport


def format_big(value: int) -> str:
    """Show large integers in scientific notation with their digit count."""
    if value < 10**12:
        return f"{value:,}"
    # Work on the decimal string: values such as 32^320 overflow a float.
    text = str(value)
    mantissa = f"{text[0]}.{text[1:4]}"
    return f"{mantissa}e+{len(text) - 1} ({len(text)} digits)"


def format_schedule(schedule: Schedule) -> str:
    """Render a schedule as a table: one row per week, one column per group."""
    if not schedule:
        return "(empty schedule)"
    num_groups = len(schedule[0])
    cells = [[",".join(map(str, group)) for group in week] for week in schedule]
    widths = [
        max(len(f"Group {k + 1}"), *(len(row[k]) for row in cells if k < len(row)))
        for k in range(num_groups)
    ]
    header = "Week    | " + " | ".join(
        f"Group {k + 1}".ljust(widths[k]) for k in range(num_groups)
    )
    lines = [header, "-" * len(header)]
    for w, row in enumerate(cells, start=1):
        lines.append(
            f"Week {w:<3}| " + " | ".join(cell.ljust(widths[k]) for k, cell in enumerate(row))
        )
    return "\n".join(lines)


def format_landscape(land: TheoreticalLandscape) -> str:
    rows = [
        ("Golfers n = g x p", f"{land.golfers} = {land.groups} x {land.group_size}"),
        ("Target weeks w", str(land.weeks)),
        ("Theoretical upper bound on weeks", str(land.week_upper_bound)),
        ("Total golfer pairs C(n,2)", format_big(land.total_pairs)),
        ("Pairs used per week g*C(p,2)", format_big(land.pairs_used_per_week)),
        ("Possible groups C(n,p)", format_big(land.possible_groups)),
        ("Naive assignments n^(n*w)", format_big(land.naive_assignments)),
        ("Permutation schedules (n!)^w", format_big(land.permutation_schedules)),
        ("Partitions per week P", format_big(land.partitions_per_week)),
        ("Partition schedules P^w", format_big(land.partition_schedules)),
        ("Canonical schedules C(P-1,w-1)", format_big(land.canonical_schedules_bound)),
        ("Search depth n*w (slots)", str(land.search_depth)),
        ("Depth with week 1 fixed", str(land.search_depth_with_fixed_week)),
        ("Max branching factor (n-1)", str(land.max_branching_factor)),
    ]
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"  {label.ljust(width)} : {value}" for label, value in rows)


def format_result(result: SearchResult, validation: ValidationReport) -> str:
    s = result.stats
    rows = [
        ("Weeks found (objective f)", f"{result.best_weeks} (target {result.target_weeks})"),
        ("Target reached", "yes" if result.target_reached else "no"),
        ("Search completed", "yes" if result.search_completed else f"no ({s.limit_reached})"),
        ("Proven maximum", "yes" if result.proven_maximum else "not proven"),
        ("Symmetry breaking", "on" if result.symmetry_breaking else "off"),
        ("Solutions counted", str(s.solutions_found)),
        ("States expanded", f"{s.states_expanded:,}"),
        ("Candidates generated", f"{s.candidates_generated:,}"),
        ("Assignments (accepted nodes)", f"{s.assignments:,}"),
        ("Rejected: pair conflict (C4)", f"{s.rejected_pair_conflict:,}"),
        ("Rejected: symmetry breaking", f"{s.rejected_symmetry:,}"),
        ("Rejected: group forward check", f"{s.rejected_forward_check:,}"),
        ("Rejected: week forward check", f"{s.rejected_week_check:,}"),
        ("Dead ends", f"{s.dead_ends:,}"),
        ("Backtracks", f"{s.backtracks:,}"),
        ("Fixed assignments (week 1)", str(s.fixed_assignments)),
        ("Max depth reached (slots)", str(s.max_depth_reached)),
        ("Fitness evaluations", f"{s.fitness_evaluations:,}"),
        ("Candidate validity ratio", f"{s.candidate_validity_ratio:.4f}"),
        ("Raw branching factor", f"{s.raw_branching_factor:.4f}"),
        ("Effective branching factor", f"{s.effective_branching_factor:.4f}"),
        ("Accepted nodes per week", ", ".join(map(str, s.nodes_per_week))),
        ("Elapsed time", f"{s.elapsed_seconds:.3f} s"),
        ("Independent validation", "PASSED" if validation.is_valid else "FAILED"),
    ]
    width = max(len(label) for label, _ in rows)
    lines = [f"  {label.ljust(width)} : {value}" for label, value in rows]
    lines.extend(f"    - {error}" for error in validation.errors[:20])
    return "\n".join(lines)
