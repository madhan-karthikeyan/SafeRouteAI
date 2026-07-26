"""
Node placer — converts a BuildingDef (room/corridor topology) into a
BuildingGraph (nodes + edges + floor plans). Python port of nodePlacer.ts.
"""

import math
from .models import (
    BuildingDef, BuildingDefRoom, BuildingGraph, BuildingNode, BuildingEdge,
    FloorPlan, Room, Vec3, FloorPlanRoomSeg,
)


def _build_room_map(def_: BuildingDef) -> dict[str, BuildingDefRoom]:
    return {r.id: r for r in def_.rooms}


def _floor_elevation(def_: BuildingDef) -> dict[int, float]:
    return {f.index: f.elevation for f in def_.floors}


def place_nodes(def_: BuildingDef) -> BuildingGraph:
    nodes: list[BuildingNode] = []
    edges: list[BuildingEdge] = []
    floors: list[FloorPlan] = []

    room_map = _build_room_map(def_)
    node_id_for_room: dict[str, str] = {}
    floor_el = _floor_elevation(def_)

    # 1. Place nodes at room centers
    for room in def_.rooms:
        center_x = room.x + room.width / 2
        center_z = room.z + room.depth / 2
        y = floor_el.get(room.floor, room.floor * 5)

        if room.isExit:
            kind = "exit"
        elif room.isStairwell:
            kind = "stairwell"
        else:
            kind = "sensor"

        node_id = f"n-{room.id}"
        node_id_for_room[room.id] = node_id

        label = "EXIT" if room.isExit else "STAIR" if room.isStairwell else room.label

        nodes.append(BuildingNode(
            id=node_id,
            kind=kind,
            floor=room.floor,
            position=Vec3(x=center_x, y=y + 0.4, z=center_z),
            label=label,
        ))

    # 2. Place junction nodes for corridor waypoints
    for corridor in def_.corridors:
        if not corridor.junctionPoints:
            continue
        for j, jp in enumerate(corridor.junctionPoints):
            junction_id = f"j-{corridor.id}-{j}"
            nodes.append(BuildingNode(
                id=junction_id,
                kind="hallway",
                floor=corridor.floor,
                position=Vec3(x=jp.x, y=jp.y + 0.4, z=jp.z),
            ))
            from_node = (
                node_id_for_room.get(corridor.fromRoom)
                if j == 0
                else f"j-{corridor.id}-{j - 1}"
            )
            to_node = (
                node_id_for_room.get(corridor.toRoom)
                if j == len(corridor.junctionPoints) - 1
                else f"j-{corridor.id}-{j + 1}"
            )
            if from_node:
                edges.append(BuildingEdge(
                    id=f"e-{corridor.id}-seg-{j}",
                    from_node=from_node,
                    to_node=junction_id,
                ))
            if to_node:
                edges.append(BuildingEdge(
                    id=f"e-{corridor.id}-seg-{j + 1}",
                    from_node=junction_id,
                    to_node=to_node,
                ))

    # 3. Create edges from corridors (connecting room nodes)
    for corridor in def_.corridors:
        from_node = node_id_for_room.get(corridor.fromRoom)
        to_node = node_id_for_room.get(corridor.toRoom)
        if not from_node or not to_node:
            continue
        if corridor.junctionPoints and len(corridor.junctionPoints) > 0:
            continue
        edges.append(BuildingEdge(
            id=f"e-{corridor.id}",
            from_node=from_node,
            to_node=to_node,
        ))

    # 4. Connect stairwells vertically
    for i in range(1, len(def_.floors)):
        lower_floor = def_.floors[i - 1]
        upper_floor = def_.floors[i]
        lower_stairs = [r for r in def_.rooms if r.isStairwell and r.floor == lower_floor.index]
        upper_stairs = [r for r in def_.rooms if r.isStairwell and r.floor == upper_floor.index]

        for ls in lower_stairs:
            us = next(
                (us for us in upper_stairs if abs(us.x - ls.x) < 2 and abs(us.z - ls.z) < 2),
                None,
            )
            if not us:
                continue
            lower_node = node_id_for_room.get(ls.id)
            upper_node = node_id_for_room.get(us.id)
            if lower_node and upper_node:
                edges.append(BuildingEdge(
                    id=f"e-stair-{ls.id}-{us.id}",
                    from_node=lower_node,
                    to_node=upper_node,
                ))

    # 5. Compute centering offset
    max_width = max(f.width for f in def_.floors)
    max_depth = max(f.depth for f in def_.floors)

    # Shift all nodes so the building is centered at origin
    for node in nodes:
        node.position.x -= max_width / 2
        node.position.z -= max_depth / 2

    # 6. Build floor plans
    for f in def_.floors:
        floor_rooms = []
        for r in def_.rooms:
            if r.floor == f.index:
                floor_rooms.append(Room(
                    id=r.id,
                    x=r.x,
                    z=r.z,
                    width=r.width,
                    depth=r.depth,
                    label=r.label,
                    type=r.type,
                ))
        floor_segs = []
        for c in def_.corridors:
            if c.floor == f.index:
                from_room = room_map.get(c.fromRoom)
                to_room = room_map.get(c.toRoom)
                fx = from_room.x + from_room.width / 2 if from_room else 0
                fz = from_room.z + from_room.depth / 2 if from_room else 0
                tx = to_room.x + to_room.width / 2 if to_room else 0
                tz = to_room.z + to_room.depth / 2 if to_room else 0
                floor_segs.append(FloorPlanRoomSeg(
                    from_=(fx - max_width / 2, fz - max_depth / 2),
                    to=(tx - max_width / 2, tz - max_depth / 2),
                    width=c.width,
                ))

        floors.append(FloorPlan(
            index=f.index,
            name=f.name,
            size={"width": f.width, "depth": f.depth},
            origin=Vec3(x=-max_width / 2, y=f.elevation, z=-max_depth / 2),
            rooms=floor_rooms,
            corridors=floor_segs,
        ))

    return BuildingGraph(
        id=def_.meta.id,
        name=def_.meta.name,
        floors=floors,
        nodes=nodes,
        edges=edges,
        hazardGrid={"cols": 32, "rows": 22},
    )
