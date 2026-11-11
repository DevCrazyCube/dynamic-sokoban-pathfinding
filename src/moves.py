# moves.py
# Handles movement logic: validating moves, pushing boxes, deadlock detection.

from src.state import State, make_state

# The four directions the player can move.
# Each maps a direction character to a (row_delta, col_delta) offset.
DIRECTIONS: dict[str, tuple[int, int]] = {
    "U": (-1, 0),  # Up    — row decreases
    "D": (1, 0),   # Down  — row increases
    "L": (0, -1),  # Left  — col decreases
    "R": (0, 1),   # Right — col increases
}


def _add(pos: tuple[int, int], delta: tuple[int, int]) -> tuple[int, int]:
    """Add a delta to a position."""
    return (pos[0] + delta[0], pos[1] + delta[1])


def is_wall(grid: list[str], pos: tuple[int, int]) -> bool:
    """Return True if pos is outside the grid bounds or is a wall '#'."""
    row, col = pos
    if row < 0 or row >= len(grid):
        return True
    if col < 0 or col >= len(grid[row]):
        return True
    return grid[row][col] == "#"


def is_corner_deadlock(
    grid: list[str],
    pos: tuple[int, int],
    targets: set[tuple[int, int]],
) -> bool:
    """Return True if a box at pos is stuck in a corner and NOT on a target.

    Simple explanation:
    A corner means two perpendicular walls are immediately adjacent to the box.
    For example: a wall directly above AND a wall directly to the left.
    If the box is already on a target, it's fine — it just stays there.
    If it is NOT on a target and is in a corner, it can never reach any target,
    so we can safely discard any state where we just pushed a box here.
    """
    if pos in targets:
        return False  # Box is already where it needs to be — not a deadlock.

    row, col = pos
    wall_above = is_wall(grid, (row - 1, col))
    wall_below = is_wall(grid, (row + 1, col))
    wall_left  = is_wall(grid, (row, col - 1))
    wall_right = is_wall(grid, (row, col + 1))

    # A corner exists when walls block both a vertical and a horizontal direction.
    return (
        (wall_above and wall_left)  or
        (wall_above and wall_right) or
        (wall_below and wall_left)  or
        (wall_below and wall_right)
    )


def apply_move(
    state: State,
    move: str,
    grid: list[str],
    targets: set[tuple[int, int]],
) -> State | None:
    """Try to apply one move and return the resulting State, or None if illegal.

    Steps:
    1. Compute where the player would move.
    2. If that cell is a wall → invalid, return None.
    3. If there is a box there:
       a. Compute where the box would be pushed.
       b. If the box destination is a wall or another box → invalid, return None.
       c. If the pushed box would be in a deadlock corner → skip, return None.
       d. Otherwise move the box.
    4. Move the player.
    5. Return the new State.
    """
    player, boxes = state
    boxes_set = set(boxes)  # For O(1) membership checks.

    delta = DIRECTIONS[move]
    new_player = _add(player, delta)

    # Step 2 — player cannot walk into a wall.
    if is_wall(grid, new_player):
        return None

    new_boxes = list(boxes)

    if new_player in boxes_set:
        # Step 3 — there is a box at the player's destination.
        box_dest = _add(new_player, delta)

        # Box cannot be pushed into a wall or another box.
        if is_wall(grid, box_dest) or box_dest in boxes_set:
            return None

        # Simple deadlock check: corner + not a target.
        if is_corner_deadlock(grid, box_dest, targets):
            return None

        # Move the box: remove from old position, add at new position.
        new_boxes = [box_dest if b == new_player else b for b in new_boxes]

    return make_state(new_player, new_boxes)
