"""
Building graph loader and transformer.

Loads the simulator building_graph.json and transforms it into
the frontend's BuildingGraph format (3 floors, 6x4 grid of nodes,
with rooms, edges, and stairwells).
"""

import json
import math
import os
from .models import BuildingGraph, FloorPlan, Room, Vec3, BuildingNode, BuildingEdge

FLOOR_COUNT = 3
FLOOR_W = 40
FLOOR_D = 28
FLOOR_H = 5
GRID_COLS = 32
GRID_ROWS = 22

GRAPH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "simulator", "data", "building_graph.json"
)

_node_id_map: dict[int, str] = {}
_reverse_map: dict[str, int] = {}


def _build_rooms(floor_w: float, floor_d: float) -> list[Room]:
    rooms = []
    cols = 4
    rows = 3
    w = floor_w / cols - 1
    d = floor_d / rows - 1
    for r in range(rows):
        for c in range(cols):
            rooms.append(Room(
                id=f"r-{r}-{c}",
                x=-floor_w / 2 + c * (floor_w / cols) + 0.5,
                z=-floor_d / 2 + r * (floor_d / rows) + 0.5,
                width=w,
                depth=d,
            ))
    return rooms


def load_graph() -> BuildingGraph:
    floors: list[FloorPlan] = []
    nodes: list[BuildingNode] = []
    edges: list[BuildingEdge] = []
    _node_id_map.clear()
    _reverse_map.clear()

    node_index = 0

    for f in range(FLOOR_COUNT):
        y = f * FLOOR_H
        floors.append(FloorPlan(
            index=f,
            name=f"Floor {f + 1}",
            size={"width": FLOOR_W, "depth": FLOOR_D},
            origin=Vec3(x=0, y=y, z=0),
            rooms=_build_rooms(FLOOR_W, FLOOR_D),
        ))

        cols = 6
        rows = 4
        cell_w = FLOOR_W / (cols + 1)
        cell_d = FLOOR_D / (rows + 1)
        floor_node_ids: list[list[str]] = []

        for r in range(rows):
            floor_node_ids.append([])
            for c in range(cols):
                node_index += 1
                numeric_id = node_index
                sid = f"n-{f}-{r}-{c}"
                is_exit = f == 0 and (
                    (r == 0 and c == 0) or (r == rows - 1 and c == cols - 1)
                )
                kind = "exit" if is_exit else ("hallway" if r in (0, rows - 1) else "sensor")
                nodes.append(BuildingNode(
                    id=sid,
                    kind=kind,
                    floor=f,
                    position=Vec3(
                        x=-FLOOR_W / 2 + (c + 1) * cell_w,
                        y=y + 0.4,
                        z=-FLOOR_D / 2 + (r + 1) * cell_d,
                    ),
                    label="EXIT" if is_exit else None,
                ))
                _node_id_map[numeric_id] = sid
                _reverse_map[sid] = numeric_id
                floor_node_ids[r].append(sid)

        for r in range(rows):
            for c in range(cols):
                nid = floor_node_ids[r][c]
                if c + 1 < cols:
                    nid2 = floor_node_ids[r][c + 1]
                    edges.append(BuildingEdge(
                        id=f"e-{nid}-{nid2}",
                        from_node=nid,
                        to_node=nid2,
                    ))
                if r + 1 < rows:
                    nid2 = floor_node_ids[r + 1][c]
                    edges.append(BuildingEdge(
                        id=f"e-{nid}-{nid2}",
                        from_node=nid,
                        to_node=nid2,
                    ))

        if f > 0:
            stair_id = f"stair-{f}"
            up_id = floor_node_ids[0][2]
            down_id = floor_node_ids[0][2]
            nodes.append(BuildingNode(
                id=stair_id,
                kind="stairwell",
                floor=f,
                position=Vec3(
                    x=-FLOOR_W / 2 + 3 * cell_w,
                    y=y,
                    z=-FLOOR_D / 2 + cell_d * 0.5,
                ),
                label=f"Stair {f}",
            ))
            edges.append(BuildingEdge(
                id=f"e-stair-{f}-up",
                from_node=up_id,
                to_node=down_id,
            ))

    return BuildingGraph(
        id="bldg-alpha",
        name="Tower Alpha",
        floors=floors,
        nodes=nodes,
        edges=edges,
        hazardGrid={"cols": GRID_COLS, "rows": GRID_ROWS},
    )


def get_numeric_id(sid: str) -> int | None:
    return _reverse_map.get(sid)


def get_string_id(numeric: int) -> str | None:
    return _node_id_map.get(numeric)
