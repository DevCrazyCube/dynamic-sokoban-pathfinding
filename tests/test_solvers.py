"""Tests for the two solvers, the dead-square table, the SVG export and the CLI.

Run from the project root:

    python -m unittest

Standard library only.
"""

import random
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from src.level_loader import LEVELS_FILE, get_level, parse_level
from src.moves import DIRECTIONS, is_wall
from src.push_solver import push_distances, solve_pushes
from src.solver import solve
from src.state import is_goal, make_state
from src.stats import SearchLimitReached, SearchStats
from src.svg_export import replay, solution_svg

ROOT = Path(__file__).resolve().parent.parent


def play(grid, state, moves):
    """Replay moves under the plain rules of Sokoban and return the last state.

    This is deliberately not the solvers' own move code: no deadlock checks, no
    shortcuts.  A move into a wall, or a push into a wall or a box, fails the test.
    """
    player, boxes = state[0], set(state[1])
    for number, move in enumerate(moves, start=1):
        dr, dc = DIRECTIONS[move]
        player = (player[0] + dr, player[1] + dc)
        if is_wall(grid, player):
            raise AssertionError(f"move {number} ({move}) walks into a wall")
        if player in boxes:
            dest = (player[0] + dr, player[1] + dc)
            if is_wall(grid, dest) or dest in boxes:
                raise AssertionError(f"move {number} ({move}) pushes a box that cannot move")
            boxes.remove(player)
            boxes.add(dest)
    return make_state(player, list(boxes))


def level(text):
    """Parse a level written as a string in the test."""
    grid, player, boxes, targets = parse_level(text.strip("\n").splitlines())
    return grid, make_state(player, boxes), targets


def random_level(rng, rows, cols, boxes):
    """A small random room: walls around, a few walls inside, boxes and targets."""
    while True:
        cells = [(r, c) for r in range(1, rows + 1) for c in range(1, cols + 1)]
        walls = {cell for cell in cells if rng.random() < 0.15}
        free = [cell for cell in cells if cell not in walls]
        if len(free) < 2 * boxes + 1:
            continue
        rng.shuffle(free)
        player = free[0]
        box_cells = free[1:1 + boxes]
        target_cells = rng.sample(free, boxes)

        lines = []
        for r in range(rows + 2):
            line = ""
            for c in range(cols + 2):
                cell = (r, c)
                if r in (0, rows + 1) or c in (0, cols + 1) or cell in walls:
                    line += "#"
                elif cell == player:
                    line += "+" if cell in target_cells else "@"
                elif cell in box_cells:
                    line += "*" if cell in target_cells else "$"
                elif cell in target_cells:
                    line += "."
                else:
                    line += " "
            lines.append(line)
        return "\n".join(lines)


class LevelsFromTheFile(unittest.TestCase):
    """The levels that ship with the project, against the lengths in their headers."""

    EXPECTED = {0: 3, 1: 6, 2: 69}

    def test_bfs_finds_the_stated_length(self):
        for index, length in self.EXPECTED.items():
            with self.subTest(level=index):
                grid, state, _boxes, targets = get_level(LEVELS_FILE, index)
                moves = solve(state, grid, targets)
                self.assertEqual(len(moves), length)
                self.assertTrue(is_goal(play(grid, state, moves), targets))

    def test_a_star_finds_the_stated_length(self):
        for index, length in self.EXPECTED.items():
            with self.subTest(level=index):
                grid, state, _boxes, targets = get_level(LEVELS_FILE, index)
                moves = solve_pushes(state, grid, targets)
                self.assertEqual(len(moves), length)
                self.assertTrue(is_goal(play(grid, state, moves), targets))

    def test_a_star_expands_fewer_states_than_bfs_on_level_2(self):
        grid, state, _boxes, targets = get_level(LEVELS_FILE, 2)
        bfs, a_star = SearchStats(), SearchStats()
        solve(state, grid, targets, bfs)
        solve_pushes(state, grid, targets, a_star)
        self.assertLess(a_star.expanded * 10, bfs.expanded)

    def test_weighted_search_solves_level_3(self):
        grid, state, _boxes, targets = get_level(LEVELS_FILE, 3)
        moves = solve_pushes(state, grid, targets, weight=5)
        self.assertTrue(is_goal(play(grid, state, moves), targets))
        # The length the README reports.  Not known to be the shortest.
        self.assertEqual(len(moves), 76)


class BothSolversAgree(unittest.TestCase):
    """A* over pushes must return a solution exactly as long as the BFS does."""

    def check(self, seed, count, rows, cols, boxes):
        rng = random.Random(seed)
        solved = 0
        for number in range(count):
            text = random_level(rng, rows, cols, boxes)
            grid, state, targets = level(text)
            expected = solve(state, grid, targets)
            found = solve_pushes(state, grid, targets)
            with self.subTest(level=number, text=text):
                if expected is None:
                    self.assertIsNone(found)
                    continue
                self.assertIsNotNone(found)
                self.assertEqual(len(found), len(expected))
                self.assertTrue(is_goal(play(grid, state, found), targets))
                solved += 1
        return solved

    def test_two_boxes(self):
        solved = self.check(seed=11, count=300, rows=5, cols=5, boxes=2)
        self.assertGreaterEqual(solved, 40)   # The sample is not all dead ends.

    def test_three_boxes(self):
        solved = self.check(seed=12, count=150, rows=5, cols=6, boxes=3)
        self.assertGreaterEqual(solved, 15)

    def test_weighted_search_stays_within_its_bound(self):
        rng = random.Random(13)
        for number in range(80):
            text = random_level(rng, 5, 6, 3)
            grid, state, targets = level(text)
            shortest = solve_pushes(state, grid, targets)
            weighted = solve_pushes(state, grid, targets, weight=4)
            with self.subTest(level=number, text=text):
                if shortest is None:
                    self.assertIsNone(weighted)
                    continue
                self.assertTrue(is_goal(play(grid, state, weighted), targets))
                self.assertGreaterEqual(len(weighted), len(shortest))
                self.assertLessEqual(len(weighted), 4 * len(shortest))


class EdgeCases(unittest.TestCase):
    def test_a_solved_level_needs_no_moves(self):
        grid, state, targets = level("""
#####
#@* #
#####
""")
        self.assertEqual(solve(state, grid, targets), [])
        self.assertEqual(solve_pushes(state, grid, targets), [])

    def test_a_box_in_a_corner_has_no_solution(self):
        grid, state, targets = level("""
#####
#$ .#
#  @#
#####
""")
        self.assertIsNone(solve(state, grid, targets))
        self.assertIsNone(solve_pushes(state, grid, targets))

    def test_two_boxes_against_a_wall_cannot_get_past_each_other(self):
        grid, state, targets = level("""
#######
#.$$ @#
#######
""")
        self.assertIsNone(solve(state, grid, targets))
        self.assertIsNone(solve_pushes(state, grid, targets))

    def test_the_limit_stops_both_searches(self):
        grid, state, _boxes, targets = get_level(LEVELS_FILE, 3)
        with self.assertRaises(SearchLimitReached):
            solve(state, grid, targets, limit=50)
        with self.assertRaises(SearchLimitReached):
            solve_pushes(state, grid, targets, limit=50)

    def test_stats_are_filled_in(self):
        grid, state, _boxes, targets = get_level(LEVELS_FILE, 1)
        for search in (solve, solve_pushes):
            stats = SearchStats()
            search(state, grid, targets, stats)
            self.assertGreater(stats.expanded, 0)
            self.assertGreaterEqual(stats.seen, stats.expanded)


class DeadSquares(unittest.TestCase):
    def test_a_box_on_the_edge_of_a_room_cannot_reach_the_middle(self):
        grid, _state, targets = level("""
#######
#     #
#     #
#  .  #
#     #
#@    #
#######
""")
        alive = push_distances(grid, targets)
        for r in range(1, 6):
            for c in range(1, 6):
                on_edge = r in (1, 5) or c in (1, 5)
                with self.subTest(cell=(r, c)):
                    self.assertEqual((r, c) not in alive, on_edge)
        self.assertEqual(alive[(3, 3)], 0)
        self.assertEqual(alive[(3, 2)], 1)
        self.assertEqual(alive[(2, 2)], 2)

    def test_a_target_on_the_wall_keeps_that_wall_alive(self):
        grid, _state, targets = level("""
#######
#  .  #
#     #
#@    #
#######
""")
        alive = push_distances(grid, targets)
        self.assertEqual(alive[(1, 2)], 1)      # Slides along the wall.
        self.assertEqual(alive[(1, 4)], 1)
        self.assertNotIn((1, 1), alive)          # A corner: nobody can push it out.
        self.assertNotIn((3, 3), alive)          # The opposite wall has no target.


class SvgExport(unittest.TestCase):
    def setUp(self):
        self.grid, self.state, _boxes, self.targets = get_level(LEVELS_FILE, 2)
        self.moves = solve_pushes(self.state, self.grid, self.targets)

    def test_replay_follows_each_box_to_a_target(self):
        frames = replay(self.state, self.moves)
        self.assertEqual(len(frames), len(self.moves) + 1)
        _player, boxes = frames[-1]
        self.assertEqual(set(boxes), self.targets)
        # The same end state as the plain replay.
        self.assertEqual(
            make_state(*frames[-1]), play(self.grid, self.state, self.moves)
        )

    def test_the_file_is_well_formed_and_animates_every_piece(self):
        text = solution_svg(self.grid, self.state, self.moves, self.targets, "Level 2 & <more>")
        root = ET.fromstring(text)
        ns = "{http://www.w3.org/2000/svg}"
        self.assertEqual(root.tag, ns + "svg")

        moving = root.findall(f".//{ns}animateTransform")
        self.assertEqual(len(moving), len(self.state[1]) + 1)   # The boxes and the player.
        for animation in moving:
            values = animation.get("values").split(";")
            times = [float(t) for t in animation.get("keyTimes").split(";")]
            self.assertEqual(len(values), len(self.moves) + 3)
            self.assertEqual(len(times), len(values))
            self.assertEqual((times[0], times[-1]), (0.0, 1.0))
            self.assertEqual(times, sorted(times))

        self.assertEqual(root.find(f"{ns}title").text, "Level 2 & <more>")
        self.assertNotIn("<script", text)


class CommandLine(unittest.TestCase):
    def run_main(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "src.main", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )

    def test_level_1(self):
        result = self.run_main("1", "--no-visualizer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Moves    : 6", result.stdout)
        self.assertIn("Shortest : yes", result.stdout)

    def test_bfs_gives_the_same_length(self):
        result = self.run_main("1", "--no-visualizer", "--solver", "bfs")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Moves    : 6", result.stdout)
        self.assertIn("BFS over moves", result.stdout)

    def test_a_reached_limit_falls_back_and_says_so(self):
        result = self.run_main("3", "--no-visualizer", "--limit", "200")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Switching to the weighted search", result.stdout)
        self.assertIn("Shortest : not proven", result.stdout)

    def test_an_explicit_limit_on_bfs_stops_with_code_2(self):
        result = self.run_main("3", "--no-visualizer", "--solver", "bfs", "--limit", "200")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Stopped", result.stdout)

    def test_a_level_that_does_not_exist(self):
        result = self.run_main("99", "--no-visualizer")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stdout)

    def test_weight_with_bfs_is_refused(self):
        result = self.run_main("0", "--solver", "bfs", "--weight", "2")
        self.assertEqual(result.returncode, 2)

    def test_svg_is_written(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "out" / "level-0.svg"
            result = self.run_main("0", "--no-visualizer", "--svg", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            ET.parse(target)


if __name__ == "__main__":
    unittest.main()
