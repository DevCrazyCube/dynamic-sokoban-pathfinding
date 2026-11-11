# main.py
# Entry point for the Sokoban solver.
#
# Usage:
#   python -m src.main [level] [--solver astar|bfs] [--weight N] [--limit N]
#                      [--svg FILE] [--no-visualizer]
#
# Examples:
#   python -m src.main                     # Solve Level 0, open visualizer
#   python -m src.main 2 --no-visualizer   # Solve Level 2, console only
#   python -m src.main 2 --solver bfs      # The same level with plain BFS
#   python -m src.main 3 --svg level-3.svg # Save the solution as an animation

import argparse
import time
from pathlib import Path

from src.level_loader import get_level, LEVELS_FILE
from src.output import (
    print_level_info, print_no_solution, print_search, print_solution,
)
from src.push_solver import solve_pushes
from src.solver import solve
from src.stats import SearchLimitReached, SearchStats
from src.svg_export import solution_svg
from src.visualizer import run_visualizer

# How many states the shortest-solution search may expand before A* switches to
# the weighted search.  About ten seconds on a laptop.
DEFAULT_LIMIT = 100_000

# The weight the search falls back on.
FALLBACK_WEIGHT = 5


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Solve a Sokoban level and step through the solution.",
    )
    parser.add_argument(
        "level", nargs="?", type=int, default=0,
        help="which level in levels/Sokoban_levels.txt to solve (default: 0)",
    )
    parser.add_argument(
        "--solver", choices=("astar", "bfs"), default="astar",
        help="astar: A* over pushes (default).  bfs: breadth-first over single moves",
    )
    parser.add_argument(
        "--weight", type=int, default=None, metavar="N",
        help="astar only.  1 finds the shortest solution; a larger weight finds "
             "one sooner that may be longer.  Default: 1, then "
             f"{FALLBACK_WEIGHT} if the limit is reached",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="stop after expanding N states.  Default: "
             f"{DEFAULT_LIMIT:,} for the shortest-solution search of astar, "
             "no limit otherwise",
    )
    parser.add_argument(
        "--svg", type=Path, default=None, metavar="FILE",
        help="save the solution as an animated SVG",
    )
    parser.add_argument(
        "--no-visualizer", action="store_true",
        help="print the solution only; do not open the window",
    )
    args = parser.parse_args()

    if args.weight is not None and args.weight < 1:
        parser.error("--weight must be 1 or more")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be 1 or more")
    if args.solver == "bfs" and args.weight is not None:
        parser.error("--weight only applies to --solver astar")
    return args


def _search(args: argparse.Namespace, initial_state, grid, targets):
    """Run the chosen solver.

    Returns (moves, name of the search, its stats, seconds, shortest?).
    `moves` is None when the level has no solution.  Raises SearchLimitReached
    when the search was stopped by --limit.
    """
    stats = SearchStats()
    began = time.perf_counter()

    if args.solver == "bfs":
        moves = solve(initial_state, grid, targets, stats, args.limit)
        return moves, "BFS over moves", stats, time.perf_counter() - began, True

    if args.weight is not None:
        moves = solve_pushes(initial_state, grid, targets, stats, args.weight, args.limit)
        name = "A* over pushes" if args.weight == 1 else f"weighted A* over pushes (weight {args.weight})"
        return moves, name, stats, time.perf_counter() - began, args.weight == 1

    # No weight given: look for the shortest solution first, within the limit.
    limit = args.limit if args.limit is not None else DEFAULT_LIMIT
    try:
        moves = solve_pushes(initial_state, grid, targets, stats, 1, limit)
        return moves, "A* over pushes", stats, time.perf_counter() - began, True
    except SearchLimitReached:
        print(
            f"No shortest solution within {limit:,} states. "
            f"Switching to the weighted search (weight {FALLBACK_WEIGHT})..."
        )

    stats = SearchStats()
    began = time.perf_counter()
    moves = solve_pushes(initial_state, grid, targets, stats, FALLBACK_WEIGHT)
    name = f"weighted A* over pushes (weight {FALLBACK_WEIGHT})"
    return moves, name, stats, time.perf_counter() - began, False


def main() -> None:
    args = _parse_args()

    # ── Load level ────────────────────────────────────────────────────────────
    grid, initial_state, box_positions, targets = get_level(LEVELS_FILE, args.level)
    player_pos = initial_state[0]
    print_level_info(args.level, player_pos, box_positions, targets)

    # ── Solve ─────────────────────────────────────────────────────────────────
    print("Solving...")
    try:
        moves, name, stats, seconds, shortest = _search(args, initial_state, grid, targets)
    except SearchLimitReached:
        print()
        print(f"Stopped: no solution within {args.limit:,} states.")
        raise SystemExit(2)
    print()

    # ── Output ────────────────────────────────────────────────────────────────
    if moves is None:
        print_no_solution()
        print_search(name, stats, seconds, None)
        raise SystemExit(1)

    print_solution(moves)
    print_search(name, stats, seconds, shortest)

    # ── Animated SVG ──────────────────────────────────────────────────────────
    if args.svg is not None:
        caption = f"Level {args.level} · {len(moves)} moves · {name}"
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(
            solution_svg(grid, initial_state, moves, targets, caption),
            encoding="utf-8",
        )
        print()
        print(f"Saved    : {args.svg}")

    # ── Visualizer ────────────────────────────────────────────────────────────
    if not args.no_visualizer:
        print()
        print("Opening visualizer… (close the window to exit)")
        run_visualizer(grid, initial_state, moves, targets)


if __name__ == "__main__":
    main()
