# main.py
# Entry point for the Sokoban solver.
#
# Usage:
#   python -m src.main [level_index] [--no-visualizer]
#
# Examples:
#   python -m src.main              # Solve Level 0, open visualizer
#   python -m src.main 1            # Solve Level 1, open visualizer
#   python -m src.main 2 --no-visualizer  # Solve Level 2, console only

import sys

from src.level_loader import get_level, LEVELS_FILE
from src.solver import solve
from src.output import print_level_info, print_solution, print_no_solution
from src.visualizer import run_visualizer


def _parse_args() -> tuple[int, bool]:
    """Parse command-line arguments.

    Returns:
        level_index     - which level to solve (default 0)
        no_visualizer   - True when --no-visualizer flag is present
    """
    args = sys.argv[1:]
    level_index = 0
    no_visualizer = False

    for arg in args:
        if arg == "--no-visualizer":
            no_visualizer = True
        elif arg.lstrip("-").isdigit():
            level_index = int(arg)
        else:
            print(f"Error: Unknown argument '{arg}'.")
            print("Usage: python -m src.main [level_index] [--no-visualizer]")
            sys.exit(1)

    return level_index, no_visualizer


def main() -> None:
    level_index, no_visualizer = _parse_args()

    # ── Load level ────────────────────────────────────────────────────────────
    grid, initial_state, box_positions, targets = get_level(LEVELS_FILE, level_index)
    player_pos = initial_state[0]
    print_level_info(level_index, player_pos, box_positions, targets)

    # ── Solve ─────────────────────────────────────────────────────────────────
    print("Solving...")
    moves = solve(initial_state, grid, targets)
    print()

    # ── Output ────────────────────────────────────────────────────────────────
    if moves is None:
        print_no_solution()
        return

    print_solution(moves)

    # ── Visualizer ────────────────────────────────────────────────────────────
    if not no_visualizer:
        print()
        print("Opening visualizer… (close the window to exit)")
        run_visualizer(grid, initial_state, moves, targets)


if __name__ == "__main__":
    main()
