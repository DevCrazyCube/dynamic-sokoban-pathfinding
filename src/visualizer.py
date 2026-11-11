# visualizer.py
# Step-through solution visualizer built with Tkinter.
#
# This is NOT a playable game.
# It shows how the solver's solution plays out, one move at a time.
# Use the Next / Previous / Reset buttons to navigate.

from src.state import State
from src.moves import apply_move, DIRECTIONS

# ── Visual constants ──────────────────────────────────────────────────────────

CELL   = 52        # Pixel size of each grid cell.
PAD    = 10        # Padding around the grid canvas.
RADIUS = 14        # Radius of the player circle (drawn inside the cell).

# Dark theme colors (Catppuccin-inspired palette).
BG         = "#1e1e2e"   # Window / canvas background.
C_WALL     = "#45475a"   # Wall cells.
C_FLOOR    = "#313244"   # Empty floor cells.
C_TARGET   = "#f9e2af"   # Target dot (small, drawn on floor).
C_BOX      = "#fab387"   # Box (not on target).
C_BOX_OK   = "#a6e3a1"   # Box sitting on a target.
C_PLAYER   = "#89b4fa"   # Player circle.
C_BTN_BG   = "#313244"   # Button background.
C_BTN_FG   = "#cdd6f4"   # Button text.
C_LABEL    = "#cdd6f4"   # Info label text.


# ── State pre-computation ─────────────────────────────────────────────────────

def _build_state_sequence(
    initial_state: State,
    moves: list[str],
    grid: list[str],
    targets: set[tuple[int, int]],
) -> list[State]:
    """Return the full list of states from start through each move.

    Simple explanation:
    We replay the solution move by move and save every intermediate state.
    The visualizer then just indexes into this list — no need to recompute
    anything when the user clicks Next or Previous.
    """
    states = [initial_state]
    current = initial_state
    for move in moves:
        nxt = apply_move(current, move, grid, targets)
        if nxt is not None:
            current = nxt
        states.append(current)
    return states


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_grid(
    canvas: "tk.Canvas",
    grid: list[str],
    state: State,
    targets: set[tuple[int, int]],
) -> None:
    """Redraw the entire grid for the given state."""
    canvas.delete("all")

    player, boxes = state
    boxes_set = set(boxes)

    rows = len(grid)
    cols = max(len(row) for row in grid) if grid else 0

    for r in range(rows):
        for c in range(cols):
            x0 = PAD + c * CELL
            y0 = PAD + r * CELL
            x1 = x0 + CELL
            y1 = y0 + CELL
            pos = (r, c)

            # Determine cell character from the clean grid.
            ch = grid[r][c] if c < len(grid[r]) else " "

            # ── Background cell ──────────────────────────────────────────────
            if ch == "#":
                canvas.create_rectangle(x0, y0, x1, y1, fill=C_WALL, outline=C_WALL)
                continue  # Nothing else to draw on a wall.
            else:
                canvas.create_rectangle(x0, y0, x1, y1, fill=C_FLOOR, outline=C_FLOOR)

            # ── Target dot (drawn beneath boxes/player) ──────────────────────
            if ch == ".":
                dot = 8  # Dot radius in pixels.
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                canvas.create_oval(
                    cx - dot, cy - dot, cx + dot, cy + dot,
                    fill=C_TARGET, outline=C_TARGET,
                )

            # ── Box ──────────────────────────────────────────────────────────
            if pos in boxes_set:
                color = C_BOX_OK if pos in targets else C_BOX
                margin = 6
                canvas.create_rectangle(
                    x0 + margin, y0 + margin,
                    x1 - margin, y1 - margin,
                    fill=color, outline=color,
                )

            # ── Player ───────────────────────────────────────────────────────
            if pos == player:
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                canvas.create_oval(
                    cx - RADIUS, cy - RADIUS,
                    cx + RADIUS, cy + RADIUS,
                    fill=C_PLAYER, outline=C_PLAYER,
                )


# ── Main entry point ──────────────────────────────────────────────────────────

def run_visualizer(
    grid: list[str],
    initial_state: State,
    moves: list[str],
    targets: set[tuple[int, int]],
) -> None:
    """Open the Tkinter visualizer window."""
    try:
        import tkinter as tk
    except ImportError:
        print("Visualizer unavailable: tkinter is not installed on this system.")
        return

    states = _build_state_sequence(initial_state, moves, grid, targets)
    total  = len(states)      # Number of steps (initial + one per move).
    index  = [0]              # Mutable int wrapped in a list for closure access.

    # ── Window setup ─────────────────────────────────────────────────────────
    try:
        root = tk.Tk()
    except tk.TclError as error:
        # No screen to open a window on (a server, a container, an SSH session).
        print(f"Visualizer unavailable: {error}")
        return
    root.title("Sokoban Solver — Step-through Visualizer")
    root.configure(bg=BG)
    root.resizable(False, False)

    # Canvas sized to fit the grid exactly.
    rows = len(grid)
    cols = max(len(row) for row in grid) if grid else 1
    canvas_w = cols * CELL + PAD * 2
    canvas_h = rows * CELL + PAD * 2

    canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, bg=BG, highlightthickness=0)
    canvas.pack()

    # ── Info labels ───────────────────────────────────────────────────────────
    info_frame = tk.Frame(root, bg=BG)
    info_frame.pack(fill="x", padx=PAD, pady=(0, 4))

    step_var = tk.StringVar()
    boxes_var = tk.StringVar()

    tk.Label(info_frame, textvariable=step_var,  bg=BG, fg=C_LABEL, font=("Courier", 11)).pack(side="left",  padx=8)
    tk.Label(info_frame, textvariable=boxes_var, bg=BG, fg=C_LABEL, font=("Courier", 11)).pack(side="right", padx=8)

    # ── Control buttons ───────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(pady=(0, PAD))

    btn_cfg = {"bg": C_BTN_BG, "fg": C_BTN_FG, "font": ("Courier", 11, "bold"),
               "relief": "flat", "padx": 16, "pady": 6, "cursor": "hand2"}

    def show(i: int) -> None:
        """Render state at index i and refresh labels."""
        i = max(0, min(i, total - 1))
        index[0] = i
        state = states[i]
        _draw_grid(canvas, grid, state, targets)

        # Count how many boxes are currently on targets.
        _, boxes = state
        on_target = sum(1 for b in boxes if b in targets)
        total_boxes = len(boxes)

        step_var.set(f"Step {i} / {total - 1}")
        boxes_var.set(f"Boxes on targets: {on_target} / {total_boxes}")

        prev_btn.config(state="normal" if i > 0        else "disabled")
        next_btn.config(state="normal" if i < total - 1 else "disabled")

    prev_btn = tk.Button(btn_frame, text="◀  Previous", command=lambda: show(index[0] - 1), **btn_cfg)
    reset_btn = tk.Button(btn_frame, text="↺  Reset",    command=lambda: show(0),             **btn_cfg)
    next_btn  = tk.Button(btn_frame, text="Next  ▶",    command=lambda: show(index[0] + 1),  **btn_cfg)

    prev_btn.pack(side="left",  padx=6)
    reset_btn.pack(side="left", padx=6)
    next_btn.pack(side="left",  padx=6)

    # ── First draw ────────────────────────────────────────────────────────────
    show(0)

    root.mainloop()
