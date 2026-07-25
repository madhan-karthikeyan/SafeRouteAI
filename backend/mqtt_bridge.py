"""
MQTT bridge — subscribes to evac/node/# and builds Snapshot objects.

Connects to the Mosquitto broker, listens for hazard and status updates
from the ESP32 mesh, aggregates them into a unified Snapshot, and
emits to registered WebSocket connections.
"""

import json
import math
import threading
import time
import paho.mqtt.client as mqtt
from .models import NodeState, NetworkStats, EvacRoute, Snapshot, BuildingNode
from .graph_service import load_graph, get_string_id, get_numeric_id
from .heatmap_service import interpolate_heatmap, diffuse_grid
from .snapshot_store import SnapshotStore

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_HAZARD = "evac/node/+/hazard"
MQTT_TOPIC_STATUS = "evac/node/+/status"

FLOOR_H = 5
FLOOR_COUNT = 3
FLOOR_W = 40
FLOOR_D = 28
SHELTER_THRESHOLD = 100000.0
BLOCK_MULTIPLIER = 1e6


class MqttBridge:
    def __init__(self, store: SnapshotStore):
        self.store = store
        self.graph = load_graph()
        self._node_states: dict[str, NodeState] = {}
        self._node_health: dict[str, str] = {}
        self._total_packets = 0
        self._crc_failures = 0
        self._active_fire_nodes: list[str] = []
        self._scenario: str = "none"
        self._status: str = "NORMAL"
        self._hazard_grids: dict[int, list[float]] = {}
        self._lock = threading.Lock()
        self._listeners: list[callable] = []
        self._last_broadcast = time.time()
        self._running = False
        self._mqtt_client: mqtt.Client | None = None
        self._heatmap_dirty = False
        self._heatmap_interval = 0.5
        self._last_heatmap_recompute = time.time()

        for f in range(FLOOR_COUNT):
            cols = 32
            rows = 22
            self._hazard_grids[f] = [0.0] * (cols * rows)

    def add_listener(self, cb: callable):
        self._listeners.append(cb)

    def remove_listener(self, cb: callable):
        if cb in self._listeners:
            self._listeners.remove(cb)

    def _on_mqtt_message(self, _client, _userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            return

        with self._lock:
            self._total_packets += 1

            if topic.endswith("/hazard"):
                self._handle_hazard(topic, payload)
            elif topic.endswith("/status"):
                self._handle_status(topic, payload)

    def _handle_hazard(self, topic: str, payload: str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self._crc_failures += 1
            return

        numeric_id = data.get("node_id")
        sid = get_string_id(numeric_id)
        if sid is None:
            sid = f"n-0-0-{numeric_id % 24}"

        temp = float(data.get("temp", 25))
        smoke_val = float(data.get("smoke", 0))
        flame = bool(data.get("flame", False))
        cost = float(data.get("cost", 0))
        smoke_norm = min(1.0, smoke_val / 1000.0)

        ns = NodeState(
            nodeId=sid,
            online=True,
            temperature=temp,
            smoke=smoke_norm,
            co=smoke_val,
            flameDetected=flame,
            occupants=2,
            nextHop=None,
            failoverTier="primary" if not flame else "secondary",
            lastSeenMs=int(time.time() * 1000),
            sensorOk=True,
        )

        self._node_states[sid] = ns
        if flame and sid not in self._active_fire_nodes:
            self._active_fire_nodes.append(sid)

        if ns.temperature > 60.0 or ns.smoke > 0.6:
            self._status = "FIRE_DETECTED"
            if any(n.flameDetected for n in self._node_states.values()):
                self._status = "EVACUATION_ACTIVE"
            if len(self._active_fire_nodes) > 3:
                self._status = "SHELTER_IN_PLACE"

        self._heatmap_dirty = True

    def _handle_status(self, topic: str, payload: str):
        parts = topic.split("/")
        if len(parts) < 3:
            return
        try:
            numeric_id = int(parts[2])
        except ValueError:
            return
        sid = get_string_id(numeric_id)
        if sid is None:
            return

        if "FAULT" in payload:
            self._node_health[sid] = payload
            if sid in self._node_states:
                self._node_states[sid].sensorOk = False
                self._node_states[sid].failoverTier = "tertiary"
        else:
            self._node_health[sid] = payload

    def _recompute_heatmaps(self):
        for f in range(FLOOR_COUNT):
            self._hazard_grids[f] = interpolate_heatmap(self.graph, self._node_states, f)
            self._hazard_grids[f] = diffuse_grid(self._hazard_grids[f])
        self._heatmap_dirty = False

    def _compute_edge_cost(self, sid_a: str, sid_b: str) -> float:
        na = next((n for n in self.graph.nodes if n.id == sid_a), None)
        nb = next((n for n in self.graph.nodes if n.id == sid_b), None)
        if not na or not nb:
            return SHELTER_THRESHOLD
        dx = na.position.x - nb.position.x
        dz = na.position.z - nb.position.z
        dy = (na.position.y - nb.position.y) * 1.5
        dist = math.hypot(math.hypot(dx, dz), dy)
        if dist < 0.01:
            return 0.0

        ns_a = self._node_states.get(sid_a)
        ns_b = self._node_states.get(sid_b)
        if not ns_a or not ns_b:
            return dist

        if ns_a.flameDetected or ns_b.flameDetected:
            return dist * BLOCK_MULTIPLIER

        T_baseline, T_critical = 25.0, 80.0
        S_baseline, S_critical = 0.0, 1000.0
        T_norm = max(0.0, min(1.0, (ns_a.temperature - T_baseline) / (T_critical - T_baseline)))
        S_norm = max(0.0, min(1.0, (ns_a.smoke * 1000.0 - S_baseline) / (S_critical - S_baseline)))
        O_norm = max(0.0, min(1.0, ns_a.occupants / 10.0))
        hazard_mult = math.exp(2.2 * T_norm + 1.6 * S_norm)
        congestion = 0.5 * O_norm * dist
        return dist * hazard_mult + congestion

    def _compute_routes(self) -> list[EvacRoute]:
        node_ids = [n.id for n in self.graph.nodes]
        exit_ids = [n.id for n in self.graph.nodes if n.kind == "exit"]
        if not exit_ids:
            return []

        adj: dict[str, list[tuple[str, float]]] = {nid: [] for nid in node_ids}
        for e in self.graph.edges:
            cost = self._compute_edge_cost(e.from_node, e.to_node)
            adj[e.from_node].append((e.to_node, cost))
            adj[e.to_node].append((e.from_node, cost))

        routes: list[EvacRoute] = []
        origin_candidates = [n.id for n in self.graph.nodes
                             if n.kind != "exit" and n.id in self._node_states]
        for src in origin_candidates[:9]:
            dist: dict[str, float] = {nid: float('inf') for nid in node_ids}
            prev: dict[str, str | None] = {nid: None for nid in node_ids}
            dist[src] = 0.0
            unvisited = set(node_ids)

            while unvisited:
                u = min(unvisited, key=lambda n: dist[n])
                unvisited.remove(u)
                if dist[u] == float('inf'):
                    break
                for v, w in adj[u]:
                    alt = dist[u] + w
                    if alt < dist[v]:
                        dist[v] = alt
                        prev[v] = u

            nearest_exit = min(exit_ids, key=lambda eid: dist[eid])
            if dist[nearest_exit] >= SHELTER_THRESHOLD:
                continue

            path: list[str] = []
            cur = nearest_exit
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            if len(path) < 2:
                continue

            routes.append(EvacRoute(
                id=f"route-{src}",
                path=path,
                priority=max(0.0, min(1.0, 1.0 - len(path) / 30.0)),
            ))

        return routes

    def _build_snapshot(self) -> Snapshot:
        now_ms = int(time.time() * 1000)
        stale = sum(1 for ns in self._node_states.values()
                    if now_ms - ns.lastSeenMs > 10000)

        routes = self._compute_routes()
        stale_list = [
            sid for sid, ns in self._node_states.items()
            if now_ms - ns.lastSeenMs > 6000
        ]

        return Snapshot(
            t=now_ms,
            status=self._status,
            scenario=self._scenario,
            nodes=dict(self._node_states),
            hazard={k: list(v) for k, v in self._hazard_grids.items()},
            routes=routes,
            network=NetworkStats(
                totalPackets=self._total_packets,
                packetsPerSec=0,
                crcFailures=self._crc_failures,
                staleNodes=stale,
                avgLatencyMs=12.0,
                websocket="connected",
            ),
            activeFireNodes=list(self._active_fire_nodes),
        )

    def start(self):
        self._running = True
        client = mqtt.Client()
        client.on_message = self._on_mqtt_message
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.subscribe(MQTT_TOPIC_HAZARD)
            client.subscribe(MQTT_TOPIC_STATUS)
            client.loop_start()
            self._mqtt_client = client
            print(f"MQTT connected to {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            print(f"MQTT connection failed: {e} — running in mock-only mode")
            self._running = False

    def stop(self):
        self._running = False
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()

    def tick(self):
        with self._lock:
            now = time.time()
            if self._heatmap_dirty and (now - self._last_heatmap_recompute >= self._heatmap_interval):
                self._recompute_heatmaps()
                self._last_heatmap_recompute = now
            snap = self._build_snapshot()
            self.store.push(snap)

        for cb in self._listeners:
            try:
                cb(snap)
            except Exception:
                pass

    def inject(self, node_id: str, scenario: str):
        with self._lock:
            self._scenario = scenario
            if scenario == "sensor_failure":
                if node_id in self._node_states:
                    self._node_states[node_id].sensorOk = False
                    self._node_states[node_id].failoverTier = "tertiary"
            elif scenario == "comm_failure":
                if node_id in self._node_states:
                    self._node_states[node_id].online = False
                    self._node_states[node_id].failoverTier = "isolated"
            else:
                if node_id not in self._active_fire_nodes:
                    self._active_fire_nodes.append(node_id)
                if node_id in self._node_states:
                    ns = self._node_states[node_id]
                    ns.flameDetected = True
                    ns.temperature = 250 if scenario == "flashover" else 80
                    ns.smoke = 0.9 if scenario == "flashover" else 0.5

    def reset(self):
        with self._lock:
            self._node_states.clear()
            self._node_health.clear()
            self._active_fire_nodes.clear()
            self._scenario = "none"
            self._status = "NORMAL"
            self._total_packets = 0
            self._crc_failures = 0
            for f in range(FLOOR_COUNT):
                cols, rows = 32, 22
                self._hazard_grids[f] = [0.0] * (cols * rows)
