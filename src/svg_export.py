# svg_export.py
# Writes a solution as one animated SVG file: the level, with the player and the
# boxes moving through every step.
#
# The file needs nothing to play: no script, no stylesheet, no font.  It opens in
# a browser and plays inside a README.  The colours are the visualizer's.

from collections import deque
from xml.sax.saxutils import escape

from src.moves import DIRECTIONS, is_wall
from src.state import State
from src.visualizer import (
    BG, C_BOX, C_BOX_OK, C_FLOOR, C_LABEL, C_PLAYER, C_TARGET, C_WALL,
)

Pos = tuple[int, int]

CELL = 44       # Size of one grid cell.
PAD = 16        # Space around the grid.
FOOTER = 46     # Room under the grid for the caption and the progress bar.


def replay(initial_state: State, moves: list[str]) -> list[tuple[Pos, list[Pos]]]:
    """Every frame of a solution: (player, boxes), with each box keeping its place
    in the list from the first frame to the last.

    The state type sorts its boxes, so a box changes index when it passes another.
    An animation has to follow one box the whole way, which is why this replays
    the moves itself.  Only the rules of the game are applied here; the moves are
    taken to be legal.
    """
    player, boxes = initial_state[0], list(initial_state[1])
    frames = [(player, list(boxes))]

    for move in moves:
        dr, dc = DIRECTIONS[move]
        player = (player[0] + dr, player[1] + dc)
        if player in boxes:
            boxes[boxes.index(player)] = (player[0] + dr, player[1] + dc)
        frames.append((player, list(boxes)))

    return frames


def _inside(grid: list[str], start: Pos) -> set[Pos]:
    """The floor cells that belong to the level: everything the player could walk
    to on an empty board.  Blank cells outside the walls are not drawn as floor."""
    cells = {start}
    todo = deque([start])
    while todo:
        cell = todo.popleft()
        for dr, dc in DIRECTIONS.values():
            nxt = (cell[0] + dr, cell[1] + dc)
            if nxt not in cells and not is_wall(grid, nxt):
                cells.add(nxt)
                todo.append(nxt)
    return cells


def _num(value: float) -> str:
    """A number as short as it can be written."""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def solution_svg(
    grid: list[str],
    initial_state: State,
    moves: list[str],
    targets: set[Pos],
    caption: str = "",
    seconds_per_move: float = 0.16,
    hold_seconds: float = 1.2,
) -> str:
    """Return the animated SVG for a solution, as text.

    The animation waits `hold_seconds`, plays one move every `seconds_per_move`,
    waits again on the solved level, and starts over.
    """
    frames = replay(initial_state, moves)
    rows = len(grid)
    cols = max((len(row) for row in grid), default=0)
    width = cols * CELL + 2 * PAD
    height = rows * CELL + 2 * PAD + FOOTER

    play = len(moves) * seconds_per_move
    total = hold_seconds + play + hold_seconds

    # One key time per frame, plus the two ends of the loop.
    times = [0.0] + [
        (hold_seconds + i * seconds_per_move) / total for i in range(len(frames))
    ] + [1.0]
    key_times = ";".join(_num(t) for t in times)

    def centre(pos: Pos) -> tuple[float, float]:
        return (PAD + pos[1] * CELL + CELL / 2, PAD + pos[0] * CELL + CELL / 2)

    def path(positions: list[Pos]) -> str:
        """The translate values for one piece, held still at both ends."""
        points = [positions[0]] + positions + [positions[-1]]
        return ";".join(f"{_num(x)},{_num(y)}" for x, y in map(centre, points))

    def moving(positions: list[Pos]) -> str:
        return (
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{path(positions)}" keyTimes="{key_times}" '
            f'dur="{_num(total)}s" repeatCount="indefinite"/>'
        )

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">',
        f"<title>{escape(caption or 'Sokoban solution')}</title>",
        f'<rect width="{width}" height="{height}" rx="14" fill="{BG}"/>',
    ]

    # The board: walls, floor, target dots.
    inside = _inside(grid, initial_state[0])
    for r in range(rows):
        for c in range(cols):
            x, y = PAD + c * CELL, PAD + r * CELL
            if (r, c) in inside:
                out.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{C_FLOOR}"/>'
                )
            elif c < len(grid[r]) and grid[r][c] == "#":
                out.append(
                    f'<rect x="{x + 1}" y="{y + 1}" width="{CELL - 2}" height="{CELL - 2}" '
                    f'rx="5" fill="{C_WALL}"/>'
                )
    for target in sorted(targets):
        x, y = centre(target)
        out.append(f'<circle cx="{_num(x)}" cy="{_num(y)}" r="6" fill="{C_TARGET}"/>')

    # The boxes.  Each one is drawn around (0, 0) and moved by its animation.
    half = CELL / 2 - 6
    for index in range(len(frames[0][1])):
        positions = [boxes[index] for _player, boxes in frames]
        x, y = centre(positions[0])

        # The colour changes only on the frames where the box gets on or off a
        # target, so only those frames are written.
        colours = [C_BOX_OK if pos in targets else C_BOX for pos in positions]
        changes = [(0.0, colours[0])]
        for i in range(1, len(colours)):
            if colours[i] != colours[i - 1]:
                changes.append((times[i + 1], colours[i]))

        out.append(
            f'<g transform="translate({_num(x)},{_num(y)})">{moving(positions)}'
            f'<rect x="{_num(-half)}" y="{_num(-half)}" width="{_num(2 * half)}" '
            f'height="{_num(2 * half)}" rx="6" fill="{colours[0]}">'
        )
        if len(changes) > 1:
            out.append(
                f'<animate attributeName="fill" calcMode="discrete" '
                f'values="{";".join(colour for _t, colour in changes)}" '
                f'keyTimes="{";".join(_num(t) for t, _colour in changes)}" '
                f'dur="{_num(total)}s" repeatCount="indefinite"/>'
            )
        out.append("</rect></g>")

    # The player.
    positions = [player for player, _boxes in frames]
    x, y = centre(positions[0])
    out.append(
        f'<g transform="translate({_num(x)},{_num(y)})">{moving(positions)}'
        f'<circle r="{_num(CELL * 0.3)}" fill="{C_PLAYER}"/>'
        f'<circle r="{_num(CELL * 0.11)}" fill="{BG}"/></g>'
    )

    # Under the board: the caption and a bar that fills while the moves play.
    bar_y = height - 14
    bar_width = width - 2 * PAD
    start, end = hold_seconds / total, (hold_seconds + play) / total
    out.append(
        f'<text x="{PAD}" y="{height - 26}" fill="{C_LABEL}" font-size="14" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
        f"{escape(caption)}</text>"
    )
    out.append(
        f'<rect x="{PAD}" y="{bar_y}" width="{bar_width}" height="4" rx="2" fill="{C_FLOOR}"/>'
    )
    out.append(
        f'<rect x="{PAD}" y="{bar_y}" width="0" height="4" rx="2" fill="{C_PLAYER}">'
        f'<animate attributeName="width" values="0;0;{bar_width};{bar_width}" '
        f'keyTimes="0;{_num(start)};{_num(end)};1" dur="{_num(total)}s" '
        f'repeatCount="indefinite"/></rect>'
    )

    out.append("</svg>")
    return "\n".join(out) + "\n"
