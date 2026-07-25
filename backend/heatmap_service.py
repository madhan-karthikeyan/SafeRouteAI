"""
Hazard heatmap grid interpolation.

Transforms per-node edge_cost values into a per-floor 2D hazard grid
using inverse-distance weighting. Frontend renders this as vertex-colored
floor planes.

Replicates the diffusion algorithm from the frontend's mockApi.ts
for visual consistency between mock and live modes.
"""

import math
from .models import BuildingGraph, NodeState

GRID_COLS = 32
GRID_ROWS = 22
FLOOR_W = 40
FLOOR_D = 28
SHELTER_THRESHOLD = 100000.0


def _node_grid_cell(node_pos: dict) -> tuple[int, int]:
    nx = (node_pos.x + FLOOR_W / 2) / FLOOR_W
    nz = (node_pos.z + FLOOR_D / 2) / FLOOR_D
    c = max(0, min(GRID_COLS - 1, int(nx * GRID_COLS)))
    r = max(0, min(GRID_ROWS - 1, int(nz * GRID_ROWS)))
    return c, r


def interpolate_heatmap(
    graph: BuildingGraph,
    nodes: dict[str, NodeState],
    floor: int,
) -> list[float]:
    grid = [0.0] * (GRID_COLS * GRID_ROWS)

    floor_nodes = [n for n in graph.nodes if n.floor == floor]
    if not floor_nodes:
        return grid

    positions = [(fn.position.x, fn.position.z) for fn in floor_nodes]
    hazards = []
    for fn in floor_nodes:
        ns = nodes.get(fn.id)
        if ns is None:
            hazards.append(0.0)
        else:
            h = min(1.0, max(0.0, ns.temperature / 400.0 * 0.6 + ns.smoke * 0.4))
            hazards.append(h)

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            gx = -FLOOR_W / 2 + (c + 0.5) * (FLOOR_W / GRID_COLS)
            gz = -FLOOR_D / 2 + (r + 0.5) * (FLOOR_D / GRID_ROWS)

            total_w = 0.0
            total_v = 0.0
            for i, (px, pz) in enumerate(positions):
                dist = math.hypot(gx - px, gz - pz)
                if dist < 0.01:
                    total_v = hazards[i]
                    total_w = 1.0
                    break
                w = 1.0 / (dist * dist)
                total_v += hazards[i] * w
                total_w += w

            if total_w > 0:
                grid[r * GRID_COLS + c] = min(1.0, total_v / total_w)

    return grid


def diffuse_grid(grid: list[float], dt: float = 0.5) -> list[float]:
    next_grid = [0.0] * (GRID_COLS * GRID_ROWS)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            i = r * GRID_COLS + c
            s = grid[i] * 4
            w = 4
            if c > 0:
                s += grid[i - 1]
                w += 1
            if c < GRID_COLS - 1:
                s += grid[i + 1]
                w += 1
            if r > 0:
                s += grid[i - GRID_COLS]
                w += 1
            if r < GRID_ROWS - 1:
                s += grid[i + GRID_COLS]
                w += 1
            next_grid[i] = min(1.0, (s / w) * (1 + 0.02 * dt))
    return next_grid
