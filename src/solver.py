# solver.py
# BFS-based Sokoban solver.
#
# Why BFS?
# BFS explores states level by level (1 move, then 2 moves, then 3, …).
# The first time we reach the goal state, we are guaranteed it is via the
# shortest possible move sequence — that's what makes BFS the right choice here.

from collections import deque

from src.state import State, is_goal
from src.moves import DIRECTIONS, apply_move


def solve(
    initial_state: State,
    grid: list[str],
    targets: set[tuple[int, int]],
) -> list[str] | None:
    """Find the shortest solution using BFS.

    Returns a list of move characters (e.g. ['L', 'L']) on success,
    or None if no solution exists.
    """
    # Fast exit: the initial state is already solved (e.g. all boxes on targets).
    if is_goal(initial_state, targets):
        return []

    # Simple explanation:
    # We store visited states to avoid exploring the same situation again.
    # Without this, BFS would loop forever between equivalent states.
    visited: set[State] = {initial_state}

    # Simple explanation:
    # parent tracks how we reached each state: state → (previous_state, move).
    # Once we find the goal, we walk backwards through this map to rebuild
    # the move sequence from start to finish.
    parent: dict[State, tuple[State, str]] = {}

    queue: deque[State] = deque([initial_state])

    while queue:
        current = queue.popleft()

        for move in DIRECTIONS:
            next_state = apply_move(current, move, grid, targets)

            if next_state is None:
                continue  # Illegal move or deadlock — skip.

            if next_state in visited:
                continue  # Already seen this state — skip.

            visited.add(next_state)
            parent[next_state] = (current, move)

            if is_goal(next_state, targets):
                # Reconstruct the move sequence by walking the parent chain.
                return _reconstruct_path(next_state, initial_state, parent)

            queue.append(next_state)

    # Queue exhausted — no solution exists for this level.
    return None


def _reconstruct_path(
    goal_state: State,
    initial_state: State,
    parent: dict[State, tuple[State, str]],
) -> list[str]:
    """Walk the parent map backwards from goal to start and return move list.

    Simple explanation:
    We know how we arrived at each state (its parent and the move taken).
    Starting from the goal, we keep asking "what was the previous state?"
    until we reach the initial state. Then we reverse the collected moves.
    """
    moves: list[str] = []
    state = goal_state

    while state != initial_state:
        prev_state, move = parent[state]
        moves.append(move)
        state = prev_state

    moves.reverse()
    return moves
