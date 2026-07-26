"""
Building-aware simulation engine.

Each building gets its own isolated SimState. Handles hazard diffusion,
node state computation, route building, and status determination.
Uses the same exponential-cost Dijkstra algorithm as firmware/routing.cpp.
"""

import math
import random
import time
from .models import (
    BuildingGraph, BuildingNode, NodeState, EvacRoute, Snapshot, NetworkStats,
)
from .node_placer import place_nodes
from .building_loader import load_building_def

# Routing constants — match firmware/src/routing.cpp exactly
ALPHA = 2.2
BETA = 1.6
GAMMA = 0.5
BLOCK_MULTIPLIER = 1e6
SHELTER_THRESHOLD = 100000.0
T_BASELINE = 25.0
T_CRITICAL = 80.0
S_CRITICAL = 1000.0
OCCUPANT_CAPACITY = 10.0
STALE_NODE_MS = 6000


def _node_grid_cell(
    node: BuildingNode, graph: BuildingGraph, cols: int, rows: int
) -> tuple[int, int]:
    floor = next((f for f in graph.floors if f.index == node.floor), None)
    if not floor:
        return (0, 0)
    w = floor.size["width"]
    d = floor.size["depth"]
    nx = (node.position.x + w / 2) / w if w > 0 else 0.5
    nz = (node.position.z + d / 2) / d if d > 0 else 0.5
    c = max(0, min(cols - 1, int(nx * cols)))
    r = max(0, min(rows - 1, int(nz * rows)))
    return (c, r)


class SimState:
    def __init__(self, building_id: str):
        def_ = load_building_def(building_id)
        self.graph = place_nodes(def_)
        self.building_id = building_id
        self.t = int(time.time() * 1000)
        self.fire_origins: dict[str, dict] = {}
        self.disabled_sensors: set[str] = set()
        self.disabled_comms: set[str] = set()
        self.hazard: dict[int, list[float]] = {}
        cols = self.graph.hazardGrid["cols"]
        rows = self.graph.hazardGrid["rows"]
        for f in self.graph.floors:
            self.hazard[f.index] = [0.0] * (cols * rows)
        self.total_packets = 0
        self.crc_failures = 0
        self.scenario = "none"
        self.occupant_count = 100


def diffuse_hazard(sim: SimState, dt: float):
    cols = sim.graph.hazardGrid["cols"]
    rows = sim.graph.hazardGrid["rows"]
    for f in sim.graph.floors:
        h = sim.hazard.get(f.index)
        if not h:
            continue
        nxt = [0.0] * len(h)
        for r in range(rows):
            for c in range(cols):
                i = r * cols + c
                total = h[i] * 4
                w = 4
                if c > 0:
                    total += h[i - 1]
                    w += 1
                if c < cols - 1:
                    total += h[i + 1]
                    w += 1
                if r > 0:
                    total += h[i - cols]
                    w += 1
                if r < rows - 1:
                    total += h[i + cols]
                    w += 1
                nxt[i] = min(1.0, (total / w) * (1 + 0.02 * dt))
        sim.hazard[f.index] = nxt

    for node_id, info in sim.fire_origins.items():
        node = next((n for n in sim.graph.nodes if n.id == node_id), None)
        if not node:
            continue
        c, r = _node_grid_cell(node, sim.graph, cols, rows)
        h = sim.hazard.get(node.floor)
        if not h:
            continue
        growth = 0.35 if info["scenario"] == "flashover" else 0.05 if info["scenario"] == "slow_smolder" else 0.15
        radius = 3 if info["scenario"] == "flashover" else 2
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                rr = r + dr
                cc = c + dc
                if rr < 0 or rr >= rows or cc < 0 or cc >= cols:
                    continue
                dist = math.hypot(dr, dc)
                if dist > radius:
                    continue
                idx = rr * cols + cc
                h[idx] = min(1.0, h[idx] + growth * (1 - dist / (radius + 1)) * dt)


def node_hazard(sim: SimState, node: BuildingNode) -> float:
    cols = sim.graph.hazardGrid["cols"]
    rows = sim.graph.hazardGrid["rows"]
    c, r = _node_grid_cell(node, sim.graph, cols, rows)
    h = sim.hazard.get(node.floor)
    if not h:
        return 0.0
    return h[r * cols + c]


def compute_occupants(sim: SimState, node: BuildingNode) -> int:
    if node.kind == "exit":
        return 0
    base = round(sim.occupant_count * 0.02) if node.kind == "hallway" else round(sim.occupant_count * 0.03)
    h = node_hazard(sim, node)
    return max(0, base - round(h * base))


def compute_edge_cost(
    sim: SimState, from_node: BuildingNode, to_node: BuildingNode
) -> float:
    """Exponential edge-cost matching firmware routing.cpp:compute_edge_cost.
    
    Combines temperature, smoke, occupancy, and flame into a single cost.
    """
    dx = from_node.position.x - to_node.position.x
    dz = from_node.position.z - to_node.position.z
    dy = (from_node.position.y - to_node.position.y) * 1.5
    base_dist = math.hypot(math.hypot(dx, dz), dy)
    if base_dist < 0.01:
        return 0.0

    h_from = node_hazard(sim, from_node)
    h_to = node_hazard(sim, to_node)
    h = max(h_from, h_to)

    flame = (h > 0.75 and from_node.id not in sim.disabled_sensors) or \
            (h > 0.75 and to_node.id not in sim.disabled_sensors)

    temp = 22 + h * 380
    smoke_norm = min(1.0, h * 1.2)
    T_norm = max(0.0, min(1.0, (temp - T_BASELINE) / (T_CRITICAL - T_BASELINE)))
    S_norm = max(0.0, min(1.0, smoke_norm))

    occ_from = compute_occupants(sim, from_node)
    occ_to = compute_occupants(sim, to_node)
    O_norm = max(0.0, min(1.0, max(occ_from, occ_to) / OCCUPANT_CAPACITY))

    hazard_mult = math.exp(ALPHA * T_norm + BETA * S_norm)
    congestion_term = GAMMA * O_norm * base_dist
    cost = base_dist * hazard_mult + congestion_term
    if flame:
        cost *= BLOCK_MULTIPLIER
    return cost


def _dijkstra(
    sim: SimState, source_id: str
) -> tuple[dict[str, float], dict[str, str | None], str | None]:
    """Full Dijkstra shortest-path — matches firmware routing.cpp:routing_compute.
    
    Returns:
        (dist, prev, nearest_exit_id) where:
        - dist[node_id] = shortest distance from source
        - prev[node_id] = previous node on shortest path
        - nearest_exit_id = the exit with lowest path cost (or None if shelter)
    """
    node_ids = [n.id for n in sim.graph.nodes]
    exit_ids = [n.id for n in sim.graph.nodes if n.kind == "exit"]

    dist: dict[str, float] = {nid: float("inf") for nid in node_ids}
    prev: dict[str, str | None] = {nid: None for nid in node_ids}
    visited: set[str] = set()

    if source_id not in dist:
        return dist, prev, None

    dist[source_id] = 0.0
    unvisited = set(node_ids)
    node_map = {n.id: n for n in sim.graph.nodes}

    while unvisited:
        u = min(unvisited, key=lambda n: dist[n])
        unvisited.remove(u)
        visited.add(u)

        if dist[u] == float("inf"):
            break

        u_node = node_map.get(u)
        if not u_node:
            continue

        for e in sim.graph.edges:
            neighbor_id: str | None = None
            if e.from_node == u:
                neighbor_id = e.to_node
            elif e.to_node == u:
                neighbor_id = e.from_node
            if not neighbor_id or neighbor_id in visited:
                continue

            v_node = node_map.get(neighbor_id)
            if not v_node:
                continue

            edge_cost = compute_edge_cost(sim, u_node, v_node)
            alt = dist[u] + edge_cost
            if alt < dist[neighbor_id]:
                dist[neighbor_id] = alt
                prev[neighbor_id] = u

    nearest_exit: str | None = None
    best_cost = float("inf")
    for eid in exit_ids:
        if dist.get(eid, float("inf")) < best_cost:
            best_cost = dist[eid]
            nearest_exit = eid

    if nearest_exit and dist.get(nearest_exit, float("inf")) >= SHELTER_THRESHOLD:
        return dist, prev, None

    return dist, prev, nearest_exit


def _extract_path(prev: dict[str, str | None], target_id: str) -> list[str]:
    """Walk the predecessor chain to build the full path."""
    path: list[str] = []
    cur: str | None = target_id
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path


def _compute_next_hop(prev: dict[str, str | None], source_id: str, target_id: str) -> str | None:
    """Walk the predecessor chain from target to find the first hop from source."""
    walk: str | None = target_id
    while walk is not None:
        p = prev.get(walk)
        if p == source_id:
            return walk
        walk = p
    return None


def compute_next_hop(sim: SimState, node: BuildingNode) -> str | None:
    """Return the next hop toward the safest exit using real Dijkstra.
    
    Matches firmware routing.cpp:routing_compute in behavior.
    """
    if node.kind == "exit":
        return None
    dist, prev, nearest_exit = _dijkstra(sim, node.id)
    if nearest_exit is None:
        return None
    return _compute_next_hop(prev, node.id, nearest_exit)


def build_node_states(sim: SimState) -> dict[str, NodeState]:
    result: dict[str, NodeState] = {}
    for n in sim.graph.nodes:
        h = node_hazard(sim, n)
        online = n.id not in sim.disabled_comms
        sensor_ok = n.id not in sim.disabled_sensors
        flame = h > 0.75 and sensor_ok
        result[n.id] = NodeState(
            nodeId=n.id,
            online=online,
            temperature=(22 + h * 380) if sensor_ok else 0,
            smoke=min(1.0, h * 1.2) if sensor_ok else 0,
            co=(h * 850) if sensor_ok else 0,
            flameDetected=flame,
            occupants=compute_occupants(sim, n),
            nextHop=compute_next_hop(sim, n),
            failoverTier=("isolated" if not online else "tertiary" if not sensor_ok else "secondary" if h > 0.6 else "primary"),
            lastSeenMs=sim.t if online else sim.t - STALE_NODE_MS * 2,
            sensorOk=sensor_ok,
        )
    return result


def build_routes(sim: SimState) -> list[EvacRoute]:
    routes: list[EvacRoute] = []
    origins = [n for n in sim.graph.nodes if n.floor > 0 and n.kind != "exit"][:8]
    node_map = {n.id: n for n in sim.graph.nodes}
    for o in origins:
        dist, prev, nearest_exit = _dijkstra(sim, o.id)
        if nearest_exit is None:
            continue
        path = _extract_path(prev, nearest_exit)
        if len(path) > 1:
            routes.append(EvacRoute(
                id=f"route-{o.id}",
                path=path,
                priority=1 - len(path) / 30,
            ))
    return routes


def compute_status(nodes: dict[str, NodeState]) -> str:
    flames = sum(1 for n in nodes.values() if n.flameDetected)
    isolated = sum(1 for n in nodes.values() if not n.online)
    if flames > 6:
        return "NO_SAFE_EXIT"
    if flames > 0 and isolated > 4:
        return "SHELTER_IN_PLACE"
    if flames > 0:
        return "EVACUATION_ACTIVE"
    if any(n.smoke > 0.4 for n in nodes.values()):
        return "FIRE_DETECTED"
    return "NORMAL"


def tick_sim(sim: SimState, delta_ms: int | None = None) -> Snapshot:
    now = int(time.time() * 1000)
    dt = min(0.5, ((delta_ms or (now - sim.t)) / 1000))
    sim.t = now

    diffuse_hazard(sim, dt * 4)

    nodes = build_node_states(sim)
    routes = build_routes(sim)
    status = compute_status(nodes)
    active_fire = [n.nodeId for n in nodes.values() if n.flameDetected]

    sim.total_packets += int(40 + random.random() * 20)
    if random.random() < 0.15:
        sim.crc_failures += 1

    hazard_dict: dict[str, list[float]] = {
        str(k): list(v) for k, v in sim.hazard.items()
    }

    return Snapshot(
        t=now,
        status=status,
        scenario=sim.scenario,
        nodes=nodes,
        hazard=hazard_dict,
        routes=routes,
        network=NetworkStats(
            totalPackets=sim.total_packets,
            packetsPerSec=40 + round(random.random() * 20),
            crcFailures=sim.crc_failures,
            staleNodes=sum(1 for n in nodes.values() if not n.online),
            avgLatencyMs=12 + round(random.random() * 10),
            websocket="connected",
        ),
        activeFireNodes=active_fire,
    )


def inject_hazard(sim: SimState, node_id: str, scenario: str):
    sim.scenario = scenario
    if scenario == "sensor_failure":
        sim.disabled_sensors.add(node_id)
    elif scenario == "comm_failure":
        sim.disabled_comms.add(node_id)
    else:
        sim.fire_origins[node_id] = {"start": time.time(), "scenario": scenario}


def reset_sim(sim: SimState):
    sim.fire_origins.clear()
    sim.disabled_sensors.clear()
    sim.disabled_comms.clear()
    for f in sim.graph.floors:
        h = sim.hazard.get(f.index)
        if h:
            for i in range(len(h)):
                h[i] = 0.0
    sim.scenario = "none"
    sim.total_packets = 0
    sim.crc_failures = 0
