# push_solver.py
# A* over pushes: the same shortest solution as the BFS in solver.py, found by
# looking at far fewer states.
#
# The BFS treats every single step as a state change.  Most steps only walk the
# player around; nothing about the puzzle changes until a box is pushed.  Here a
# state changes only on a push:
#
#   state  = (player position right after a push, box positions)
#   edge   = "walk to the far side of a box, then push it one cell"
#   cost   = steps walked + 1 for the push
#
# Any solution is a row of walks and pushes, and the cheapest walk between two
# pushes is a shortest path, so the cheapest route through this graph has
# exactly as many moves as the shortest solution the BFS finds.
#
# Three things keep the search small:
#   - dead squares: cells from which a box can never be pushed to any target.
#     A push onto one is never tried.  (The corner check in moves.py is the
#     simplest case of this.)
#   - frozen squares: four cells in a 2x2 block that are all wall or box can
#     never move again.  If one of those boxes is not on a target, the state is
#     lost and is dropped.
#   - a lower bound for A*: for every box, the fewest pushes it needs to reach
#     its nearest target on an otherwise empty board.  A push moves one box one
#     cell and costs at least one move, so the bound never overestimates and the
#     first solution A* takes off the queue is a shortest one.
#
# To keep millions of states in memory, the floor cells are numbered and a state
# is one integer: a bit per cell that holds a box, and the player's cell number
# in the lowest bits.

import heapq
from collections import deque

from src.moves import DIRECTIONS, is_wall
from src.state import State, is_goal
from src.stats import SearchLimitReached, SearchStats

Pos = tuple[int, int]

# Direction letters in a fixed order.  The opposite of direction d is d ^ 1
# (U <-> D, L <-> R), which is why the order matters.
LETTERS = "UDLR"
assert list(DIRECTIONS) == list(LETTERS)


def push_distances(grid: list[str], targets: set[Pos]) -> dict[Pos, int]:
    """Fewest pushes a box needs from each cell to its nearest target.

    Computed backwards: start with a box on a target and *pull* it.  A box can
    be pulled from `cell` to `cell + d` when the puller has room to stand on
    `cell + d` and step back to `cell + 2d`.  That is the mirror image of a
    push from `cell + d` to `cell` with the player on `cell + 2d`.

    Only walls count; other boxes are ignored.  A cell that is missing from the
    result is a dead square: no row of pushes takes a box from there to a target.
    """
    dist: dict[Pos, int] = {target: 0 for target in targets}
    queue: deque[Pos] = deque(targets)

    while queue:
        cell = queue.popleft()
        for dr, dc in DIRECTIONS.values():
            came_from = (cell[0] + dr, cell[1] + dc)
            player_stood = (cell[0] + 2 * dr, cell[1] + 2 * dc)
            if came_from in dist:
                continue
            if is_wall(grid, came_from) or is_wall(grid, player_stood):
                continue
            dist[came_from] = dist[cell] + 1
            queue.append(came_from)

    return dist


class _Board:
    """The level with its floor cells numbered, ready for integer states."""

    def __init__(self, grid: list[str], player: Pos, targets: set[Pos]) -> None:
        # Number every cell the player could ever stand on: flood from the start,
        # ignoring boxes.  Anything else is as good as a wall.
        self.cells: list[Pos] = [player]
        self.index: dict[Pos, int] = {player: 0}
        todo: deque[Pos] = deque([player])
        while todo:
            cell = todo.popleft()
            for dr, dc in DIRECTIONS.values():
                nxt = (cell[0] + dr, cell[1] + dc)
                if nxt in self.index or is_wall(grid, nxt):
                    continue
                self.index[nxt] = len(self.cells)
                self.cells.append(nxt)
                todo.append(nxt)

        count = len(self.cells)

        # step[cell][d]: the neighbouring cell number in direction d, -1 for none.
        self.step: list[tuple[int, ...]] = [
            tuple(
                self.index.get((r + dr, c + dc), -1)
                for dr, dc in DIRECTIONS.values()
            )
            for r, c in self.cells
        ]

        self.target_mask = 0
        for target in targets:
            if target in self.index:
                self.target_mask |= 1 << self.index[target]

        # to_target[cell]: pushes to the nearest target, -1 on a dead square.
        distances = push_distances(grid, targets)
        self.to_target: list[int] = [distances.get(cell, -1) for cell in self.cells]

        # frozen[cell]: for each 2x2 block the cell is part of, the bits of the
        # block's floor cells (its other cells are wall).  When all of those hold
        # a box the block can never move.  Blocks whose floor cells are all
        # targets are left out: boxes frozen on targets are fine.
        self.frozen: list[tuple[int, ...]] = []
        for r, c in self.cells:
            blocks: list[int] = []
            for top in (r - 1, r):
                for left in (c - 1, c):
                    bits = 0
                    for cell in (
                        (top, left), (top, left + 1),
                        (top + 1, left), (top + 1, left + 1),
                    ):
                        if cell in self.index:
                            bits |= 1 << self.index[cell]
                    if bits & ~self.target_mask:
                        blocks.append(bits)
            self.frozen.append(tuple(blocks))

        # A state is boxes << player_bits | player.
        self.player_bits = max(1, (count - 1).bit_length())
        self.player_mask = (1 << self.player_bits) - 1

    def walk(self, start: int, boxes: int) -> list[int]:
        """Steps from start to every cell, -1 where the player cannot walk."""
        steps = [-1] * len(self.cells)
        steps[start] = 0
        todo = deque([start])
        step = self.step
        while todo:
            cell = todo.popleft()
            further = steps[cell] + 1
            for nxt in step[cell]:
                if nxt < 0 or steps[nxt] >= 0 or boxes >> nxt & 1:
                    continue
                steps[nxt] = further
                todo.append(nxt)
        return steps

    def walk_path(self, start: int, goal: int, boxes: int) -> list[str]:
        """The move letters of a shortest walk from start to goal."""
        came: dict[int, tuple[int, int]] = {}
        seen = {start}
        todo = deque([start])
        while todo and goal not in seen:
            cell = todo.popleft()
            for d, nxt in enumerate(self.step[cell]):
                if nxt < 0 or nxt in seen or boxes >> nxt & 1:
                    continue
                seen.add(nxt)
                came[nxt] = (cell, d)
                todo.append(nxt)

        letters: list[str] = []
        cell = goal
        while cell != start:
            cell, d = came[cell]
            letters.append(LETTERS[d])
        letters.reverse()
        return letters


def solve_pushes(
    initial_state: State,
    grid: list[str],
    targets: set[Pos],
    stats: SearchStats | None = None,
    weight: int = 1,
    limit: int | None = None,
) -> list[str] | None:
    """Find a solution with A* over pushes.

    With weight 1 (the default) the solution has the fewest moves possible.  A
    larger weight makes the search lean on the lower bound: it finds a solution
    sooner and in less memory, but that solution may be longer than the shortest
    (never more than `weight` times as long).

    Returns the move letters, [] when the level starts solved, or None when no
    solution exists.  `stats`, when given, is filled in as the search runs.
    With a `limit`, SearchLimitReached is raised once that many states have been
    expanded without an answer.
    """
    if stats is None:
        stats = SearchStats()

    if is_goal(initial_state, targets):
        return []

    start_player, start_boxes = initial_state
    board = _Board(grid, start_player, targets)

    boxes = 0
    for box in start_boxes:
        if box in board.index:
            boxes |= 1 << board.index[box]
        elif box not in targets:
            return None  # A box the player can never get to, and not on a target.

    step = board.step
    to_target = board.to_target
    frozen = board.frozen
    target_mask = board.target_mask
    player_bits = board.player_bits
    player_mask = board.player_mask

    def bound(mask: int) -> int:
        """Lower bound on the moves still needed; -1 when a box is stuck."""
        total = 0
        while mask:
            low = mask & -mask
            pushes = to_target[low.bit_length() - 1]
            if pushes < 0:
                return -1
            total += pushes
            mask ^= low
        return total

    start_bound = bound(boxes)
    if start_bound < 0:
        return None  # A box starts on a dead square.

    start = boxes << player_bits | board.index[start_player]

    # state -> fewest moves found so far.
    best: dict[int, int] = {start: 0}
    # state -> the state before the push and the push itself, packed:
    # ((previous state << player_bits | box) << 2) | direction.
    parent: dict[int, int] = {}

    # Queue entries: (moves so far + weight * bound, -moves so far, state).
    # On a tie the state with more moves behind it goes first: it is closer.
    queue: list[tuple[int, int, int]] = [(weight * start_bound, 0, start)]
    stats.seen = 1

    while queue:
        _estimate, neg_moves, state = heapq.heappop(queue)
        moves = -neg_moves
        if moves > best[state]:
            continue  # A cheaper route to this state was found after it was queued.

        boxes = state >> player_bits
        player = state & player_mask

        if not boxes & ~target_mask:
            return _moves_to(state, start, parent, board)

        if limit is not None and stats.expanded >= limit:
            raise SearchLimitReached

        stats.expanded += 1
        reach = board.walk(player, boxes)
        here = bound(boxes)

        rest = boxes
        while rest:
            low = rest & -rest
            rest ^= low
            box = low.bit_length() - 1
            box_step = step[box]

            for d in range(4):
                dest = box_step[d]          # Where the box ends up.
                stand = box_step[d ^ 1]     # Where the player pushes from.

                if dest < 0 or stand < 0 or reach[stand] < 0:
                    continue
                if boxes >> dest & 1 or to_target[dest] < 0:
                    continue

                new_boxes = boxes ^ low | 1 << dest

                is_frozen = False
                for block in frozen[dest]:
                    if new_boxes & block == block:
                        is_frozen = True
                        break
                if is_frozen:
                    continue

                new_state = new_boxes << player_bits | box
                new_moves = moves + reach[stand] + 1
                known = best.get(new_state)
                if known is None:
                    stats.seen += 1
                elif known <= new_moves:
                    continue

                best[new_state] = new_moves
                parent[new_state] = (state << player_bits | box) << 2 | d
                remaining = here - to_target[box] + to_target[dest]
                heapq.heappush(
                    queue, (new_moves + weight * remaining, -new_moves, new_state)
                )

    return None


def _moves_to(goal: int, start: int, parent: dict[int, int], board: _Board) -> list[str]:
    """Turn the chain of pushes back into single moves: each walk, then its push."""
    pushes: list[tuple[int, int, int]] = []   # (state before, box, direction)
    state = goal
    while state != start:
        packed = parent[state]
        d = packed & 3
        packed >>= 2
        box = packed & board.player_mask
        state = packed >> board.player_bits
        pushes.append((state, box, d))
    pushes.reverse()

    moves: list[str] = []
    for before, box, d in pushes:
        boxes = before >> board.player_bits
        player = before & board.player_mask
        stand = board.step[box][d ^ 1]
        moves.extend(board.walk_path(player, stand, boxes))
        moves.append(LETTERS[d])
    return moves
