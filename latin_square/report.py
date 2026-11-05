"""Plain-text output for Latin Square runs."""

from __future__ import annotations

from .landscape import TheoreticalLandscape
from .solver import SearchResult
from .validator import ValidationReport


def format_big(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value < 10**12:
        return f"{value:,}"
    text = str(value)
    return f"{text[0]}.{text[1:4]}e+{len(text) - 1}"


def _table(rows: list[tuple[str, str]]) -> str:
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"  {label.ljust(width)} : {value}" for label, value in rows)


def format_landscape(land: TheoreticalLandscape) -> str:
    return _table([
        ("Order n / cells n^2", f"{land.n} / {land.cells}"),
        ("Free cells D (search depth)", str(land.free_cells)),
        ("Naive assignments n^D", format_big(land.naive_assignments)),
        ("Row-permutation bound (n!)^n", format_big(land.row_permutation_bound)),
        ("Unpruned tree nodes sum n^d", format_big(land.full_tree_nodes)),
        ("Unpruned IDDFS nodes", format_big(land.iddfs_unpruned_nodes)),
        ("Latin squares L(n) (literature)", format_big(land.known_latin_squares)),
        ("Reduced squares R(n) (literature)", format_big(land.known_reduced_squares)),
        ("Max branching factor", str(land.max_branching_factor)),
    ])


def format_iterations(result: SearchResult) -> str:
    header = (f"  {'limit':>5} {'visited':>11} {'expanded':>11} {'rejected':>11} "
              f"{'backtracks':>11} {'cutoffs':>10} {'max depth':>9}  outcome")
    lines = [header, "  " + "-" * (len(header) - 2)]
    for it in result.stats.iterations:
        lines.append(
            f"  {it.depth_limit:>5} {it.nodes_visited:>11,} {it.nodes_expanded:>11,} "
            f"{it.rejected_conflicts:>11,} {it.backtracks:>11,} {it.cutoffs:>10,} "
            f"{it.max_depth:>9}  {it.outcome}"
        )
    return "\n".join(lines)


def format_result(result: SearchResult, validation: ValidationReport | None) -> str:
    s = result.stats
    rows = [
        ("Status", result.status),
        ("Search completed", "yes" if result.search_completed else f"no ({s.limit_reached})"),
        ("IDDFS iterations", str(len(s.iterations))),
        ("Solutions found", str(s.solutions_found)),
        ("Nodes visited (all iterations)", f"{s.nodes_visited:,}"),
        ("Nodes visited (last iteration)", f"{s.final_iteration_nodes:,}"),
        ("Repeated-work ratio", f"{s.repeated_work_ratio:,.2f}"),
        ("Nodes expanded", f"{s.nodes_expanded:,}"),
        ("Values tried", f"{s.values_tried:,}"),
        ("Invalid assignments (rejected)", f"{s.rejected_conflicts:,}"),
        ("Valid assignments", f"{s.assignments:,}"),
        ("Backtracks", f"{s.backtracks:,}"),
        ("Dead ends", f"{s.dead_ends:,}"),
        ("Effective branching factor", f"{s.effective_branching_factor:.3f}"),
        ("Elapsed time", f"{s.elapsed_seconds:.3f} s"),
    ]
    if validation is not None:
        rows.append(("Independent validation", "PASSED" if validation.is_valid else "FAILED"))
    text = _table(rows)
    if validation is not None:
        text += "".join(f"\n    - {e}" for e in validation.errors[:20])
    return text
