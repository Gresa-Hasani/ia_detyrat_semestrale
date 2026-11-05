"""Plain-text output for Sudoku runs."""

from __future__ import annotations

from .landscape import VALID_COMPLETE_GRIDS, TheoreticalLandscape
from .solver import SearchResult
from .validator import ValidationReport


def format_big(value: int) -> str:
    if value < 10**12:
        return f"{value:,}"
    text = str(value)
    return f"{text[0]}.{text[1:4]}e+{len(text) - 1}"


def _table(rows: list[tuple[str, str]]) -> str:
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"  {label.ljust(width)} : {value}" for label, value in rows)


def format_landscape(land: TheoreticalLandscape) -> str:
    return _table([
        ("Clues", str(land.clues)),
        ("Empty cells E (search depth)", str(land.empty_cells)),
        ("Naive bound 9^E", format_big(land.naive_bound)),
        ("Initial domain product", format_big(land.domain_product_bound)),
        ("Total initial candidates", str(land.total_candidates)),
        ("Average domain size", f"{land.average_domain_size:.3f}"),
        ("Domain size min / max", f"{land.min_domain_size} / {land.max_domain_size}"),
        ("Cells with a single candidate", str(land.singleton_cells)),
        ("Valid complete grids (literature)", format_big(VALID_COMPLETE_GRIDS)),
    ])


def format_result(result: SearchResult, validation: ValidationReport | None,
                  difficulty: str | None) -> str:
    s = result.stats
    rows = [
        ("Status", result.status),
        ("Variable order", result.variable_order),
        ("Search completed", "yes" if result.search_completed else f"no ({s.limit_reached})"),
        ("Solutions found", str(s.solutions_found)),
        ("States expanded (dequeued)", f"{s.states_expanded:,}"),
        ("States generated (enqueued)", f"{s.states_generated:,}"),
        ("Candidates tested", f"{s.candidates_tested:,}"),
        ("Invalid partial states (conflict)", f"{s.rejected_conflicts:,}"),
        ("Dead ends pruned (forward check)", f"{s.pruned_dead_ends:,}"),
        ("Failed expansions (dead branches)", f"{s.failed_expansions:,}"),
        ("Backtracks", f"{s.backtracks:,}"),
        ("Duplicate states skipped", f"{s.duplicates_skipped:,}"),
        ("Max queue size", f"{s.max_queue_size:,}"),
        ("Max depth reached", f"{s.max_depth} / {s.initial_empty}"),
        ("Raw branching factor", f"{s.raw_branching_factor:.3f}"),
        ("Consistent branching factor", f"{s.consistent_branching_factor:.3f}"),
        ("Effective branching factor", f"{s.effective_branching_factor:.3f}"),
        ("Widest BFS level", _widest_level(s.frontier_per_depth)),
        ("Elapsed time", f"{s.elapsed_seconds:.3f} s"),
    ]
    if difficulty:
        rows.append(("Measured difficulty", difficulty))
    if validation is not None:
        rows.append(("Independent validation", "PASSED" if validation.is_valid else "FAILED"))
    text = _table(rows)
    if validation is not None:
        text += "".join(f"\n    - {e}" for e in validation.errors[:20])
    return text


def _widest_level(levels: list[int]) -> str:
    if not levels:
        return "-"
    depth = max(range(len(levels)), key=levels.__getitem__)
    return f"{levels[depth]:,} states at depth {depth}"
