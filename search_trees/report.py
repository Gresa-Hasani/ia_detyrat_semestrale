"""Plain-text statistics shared by the three search-tree problems."""

from __future__ import annotations

from .core import SearchTree


def format_stats(tree: SearchTree) -> str:
    s = tree.stats
    goal = tree.goal
    rows = [
        ("Strategy", tree.strategy.upper()),
        ("Goal found", f"yes, depth {goal.depth}" if goal else "no"),
        ("Search completed", "yes" if s.limit_reached is None else f"no ({s.limit_reached})"),
        ("Goals found", str(s.goals_found)),
        ("Tree nodes generated", f"{s.nodes_generated:,}"),
        ("Nodes expanded", f"{s.nodes_expanded:,}"),
        ("Transitions examined", f"{s.transitions_examined:,}"),
        ("Valid transitions", f"{s.valid_transitions:,}"),
        ("Invalid transitions (leaves)", f"{s.invalid_transitions:,}"),
        ("Duplicate states (leaves)", f"{s.duplicates:,}"),
        ("Depth-limit leaves", f"{s.depth_limit_leaves:,}"),
        ("Dead ends (no new child)", f"{s.dead_ends:,}"),
        ("Unique states generated", f"{s.unique_states:,}"),
        ("Max tree depth", str(s.max_depth)),
        ("Max depth of a new state", str(s.max_new_state_depth)),
        ("Max frontier size", f"{s.max_frontier:,}"),
        ("Raw branching factor", f"{s.raw_branching_factor:.3f}"),
        ("Valid branching factor", f"{s.valid_branching_factor:.3f}"),
        ("Effective branching factor", f"{s.effective_branching_factor:.3f}"),
        ("Elapsed time", f"{s.elapsed_seconds:.3f} s"),
    ]
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"  {label.ljust(width)} : {value}" for label, value in rows)
