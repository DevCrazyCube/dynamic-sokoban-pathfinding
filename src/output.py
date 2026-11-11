# output.py
# Handles all console output for the Sokoban solver.
# Kept in one place so formatting is consistent and easy to change.


def print_level_info(
    level_index: int,
    player_pos: tuple[int, int],
    box_positions: list[tuple[int, int]],
    targets: set[tuple[int, int]],
) -> None:
    """Print a summary of the loaded level."""
    print(f"Level {level_index} loaded.")
    print(f"Player   : {player_pos}")
    print(f"Boxes    : {box_positions}")
    print(f"Targets  : {sorted(targets)}")
    print()


def print_solution(moves: list[str]) -> None:
    """Print the solution move sequence and total move count."""
    if moves:
        print(f"Solution : {' '.join(moves)}")
    else:
        print("Solution : (already solved)")
    print(f"Moves    : {len(moves)}")


def print_no_solution() -> None:
    """Print a clean message when no solution is found."""
    print("No solution found.")


def print_search(name: str, stats, seconds: float, shortest: bool | None) -> None:
    """Print which search ran, how much work it did, and what the answer is worth.

    `shortest` is True when the search guarantees the fewest moves, False when it
    does not, and None when there is no solution to say it about.
    """
    print(f"Search   : {name}")
    # A weighted search can expand one state several times (it reopens a state
    # when it finds a shorter way to it), so expansions can exceed distinct states.
    print(f"States   : {stats.expanded:,} expansions, {stats.seen:,} distinct states reached")
    print(f"Time     : {seconds:.2f} s")
    if shortest is True:
        print("Shortest : yes")
    elif shortest is False:
        print("Shortest : not proven (a weighted search can return a longer solution)")
