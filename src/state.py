# state.py
# Defines the State type and helpers for checking goals.
#
# A state captures everything the solver needs to know about a game situation:
#   - where the player is
#   - where all boxes are
#
# We store it as a plain Python tuple so it is hashable (can go in a set/dict).

# Simple explanation:
# State = (player_position, box_positions)
# player_position is a (row, col) tuple.
# box_positions is a sorted tuple of (row, col) tuples.
# Sorting ensures two states with the same boxes in different insertion order
# are treated as identical — which is what we want.

# Type alias for readability throughout the project.
# A State is fully hashable and comparable with == by default.
State = tuple[tuple[int, int], tuple[tuple[int, int], ...]]


def make_state(
    player: tuple[int, int],
    boxes: list[tuple[int, int]],
) -> State:
    """Build a canonical, hashable State from player position and box list."""
    # Sort boxes so that state identity does not depend on the order we
    # discovered or moved the boxes.
    return (player, tuple(sorted(boxes)))


def is_goal(state: State, targets: set[tuple[int, int]]) -> bool:
    """Return True when every box sits on a target position."""
    # Simple explanation:
    # The second element of a state is the box positions tuple.
    # We just check that every box is inside the target set.
    _player, boxes = state
    return all(box in targets for box in boxes)
