# Dynamic Sokoban Pathfinding

A Python Sokoban solver that finds the **optimal (minimum-move) solution** to a Sokoban level using **Breadth-First Search (BFS)**, with a simple step-through visualizer built in Tkinter.

---

## Project Structure

```
src/
  __init__.py      # Makes src/ a Python package
  main.py          # Entry point — ties everything together
  level_loader.py  # Reads and parses the level file
  state.py         # Hashable State type and goal check
  moves.py         # Movement logic, wall checks, deadlock detection
  solver.py        # BFS solver with path reconstruction
  output.py        # Console output formatting
  visualizer.py    # Tkinter step-through visualizer

levels/
  Sokoban_levels.txt   # Level definitions (Levels 0–3)
```

---

## Usage

Run from the **project root directory**:

```bash
# Solve Level 0 and open the visualizer
python -m src.main

# Solve a specific level
python -m src.main 1

# Console output only (no visualizer window)
python -m src.main 0 --no-visualizer

# Solve Level 2 without visualizer
python -m src.main 2 --no-visualizer
```

No external packages required — only the Python standard library.

---

## Example Output

```
Level 0 loaded.
Player   : (1, 3)
Boxes    : [(1, 1), (1, 5)]
Targets  : [(1, 2), (1, 4)]

Solving...

Solution : L R
Moves    : 2
```

---

## Level File Format

Levels are stored in `levels/Sokoban_levels.txt`:

```
Level 0 (3 steps):
#######
#.$@$.#
#######
```

| Symbol | Meaning            |
|--------|--------------------|
| `#`    | Wall               |
| `@`    | Player             |
| `$`    | Box                |
| `.`    | Target             |
| `*`    | Box on target      |
| ` `    | Empty floor        |

---

## Algorithm

### BFS (Breadth-First Search)

BFS explores all reachable states in order of increasing move count.
The first time we reach the goal state, the path to it is guaranteed to be the shortest.

```
queue   <- [initial_state]
visited <- {initial_state}
parent  <- {}   # state -> (parent_state, move)

while queue not empty:
    current <- queue.pop_left()
    for each move in [U, D, L, R]:
        next <- apply_move(current, move)
        if next is valid and not visited:
            visited.add(next)
            parent[next] = (current, move)
            if next is goal -> reconstruct path and return
            queue.append(next)
```

### State Representation

```python
State = (player_position, tuple(sorted(box_positions)))
#        (row, col)         sorted for consistent comparison
```

States are plain Python tuples — fully hashable, no extra overhead.

### Simple Deadlock Detection

After pushing a box, we check if it is stuck in a **corner**:
two perpendicular adjacent walls (e.g. a wall above and a wall to the left).
If the box is in a corner and **not** on a target, it can never reach a target,
so we discard that state immediately without expanding it further.

---

## Visualizer

The Tkinter visualizer shows the solver's solution step by step.

- **Next** / **Previous** — move one step forward or back
- **Reset** — jump back to the initial state
- Displays current step index and how many boxes are on targets

Color guide:

| Color         | Meaning           |
|---------------|-------------------|
| Dark gray     | Wall              |
| Dark blue     | Floor             |
| Yellow dot    | Target            |
| Orange square | Box               |
| Green square  | Box on target     |
| Blue circle   | Player            |
