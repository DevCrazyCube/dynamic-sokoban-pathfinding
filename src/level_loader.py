# level_loader.py
# Reads the Sokoban level file and parses individual levels.
#
# The file contains multiple levels separated by header lines like:
#   "Level 0 (3 steps):"  or  "Level 1:"
# Everything between two headers is the grid for that level.

import re
import sys
from pathlib import Path

from src.state import make_state, State

# Path to the level file relative to the project root.
LEVELS_FILE = Path(__file__).parent.parent / "levels" / "Sokoban_levels.txt"

# Regex that matches any "Level N ..." header line.
_HEADER_RE = re.compile(r"^\s*Level\s+\d+", re.IGNORECASE)


def load_levels(filepath: Path) -> list[list[str]]:
    """Read the file and split it into a list of raw grid line-groups.

    Each group is a list of strings (the grid rows) with the header already
    stripped out and blank separator lines between levels removed.
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Level file not found: {filepath}")
        sys.exit(1)

    levels: list[list[str]] = []
    current: list[str] = []

    for line in text.splitlines():
        if _HEADER_RE.match(line):
            # Start of a new level — save whatever we collected so far.
            if current:
                levels.append(current)
            current = []
        else:
            current.append(line)

    # Don't forget the last level in the file.
    if current:
        levels.append(current)

    # Remove purely empty groups (in case the file starts with blank lines).
    levels = [g for g in levels if any(line.strip() for line in g)]

    return levels


def parse_level(
    raw_lines: list[str],
) -> tuple[list[str], tuple[int, int], list[tuple[int, int]], set[tuple[int, int]]]:
    """Convert raw grid lines into structured game data.

    Returns:
        grid          - list of strings (clean grid; only '#', '.', ' ')
        player_pos    - (row, col) of the player start position
        box_positions - list of (row, col) for each box
        targets       - set of (row, col) for each target square
    """
    # Simple explanation:
    # We scan every character of every row.
    # Depending on the symbol we record the player, boxes, and targets,
    # then store a 'clean' character in the grid for collision checks.

    player_pos: tuple[int, int] | None = None
    box_positions: list[tuple[int, int]] = []
    targets: set[tuple[int, int]] = set()
    grid: list[str] = []

    # Find the maximum row width so we can pad shorter rows.
    max_width = max((len(line) for line in raw_lines if line.strip()), default=0)

    for row, line in enumerate(raw_lines):
        # Pad to max_width so grid[r][c] never raises IndexError.
        padded = line.ljust(max_width)
        clean_row: list[str] = []

        for col, ch in enumerate(padded):
            pos = (row, col)
            if ch == "@":
                # Player on empty floor.
                player_pos = pos
                clean_row.append(" ")
            elif ch == "+":
                # Player standing on a target.
                player_pos = pos
                targets.add(pos)
                clean_row.append(".")
            elif ch == "$":
                # Box on empty floor.
                box_positions.append(pos)
                clean_row.append(" ")
            elif ch == "*":
                # Box sitting on a target.
                box_positions.append(pos)
                targets.add(pos)
                clean_row.append(".")
            elif ch == ".":
                targets.add(pos)
                clean_row.append(".")
            else:
                # '#' (wall) or ' ' (floor) — keep as-is.
                clean_row.append(ch)

        grid.append("".join(clean_row))

    if player_pos is None:
        print("Error: No player '@' found in level.")
        sys.exit(1)

    return grid, player_pos, box_positions, targets


def get_level(
    filepath: Path,
    index: int,
) -> tuple[list[str], State, list[tuple[int, int]], set[tuple[int, int]]]:
    """Load and parse a single level by index.

    Returns:
        grid          - clean grid for collision checks
        initial_state - the starting State (player_pos, sorted box tuple)
        box_positions - list form of boxes (for readable output)
        targets       - set of target positions
    """
    levels = load_levels(filepath)

    if index < 0 or index >= len(levels):
        print(f"Error: Level {index} does not exist. File has {len(levels)} level(s) (0–{len(levels)-1}).")
        sys.exit(1)

    grid, player_pos, box_positions, targets = parse_level(levels[index])
    initial_state = make_state(player_pos, box_positions)
    return grid, initial_state, box_positions, targets
