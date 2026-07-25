from pydantic import BaseModel
from typing import Optional


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class BuildingNode(BaseModel):
    id: str
    kind: str  # sensor | hallway | exit | stairwell
    floor: int
    position: Vec3
    label: Optional[str] = None


class BuildingEdge(BaseModel):
    id: str
    from_node: str
    to_node: str


class Room(BaseModel):
    id: str
    x: float
    z: float
    width: float
    depth: float
    label: Optional[str] = None


class FloorPlan(BaseModel):
    index: int
    name: str
    size: dict
    origin: Vec3
    rooms: list[Room]


class BuildingGraph(BaseModel):
    id: str
    name: str
    floors: list[FloorPlan]
    nodes: list[BuildingNode]
    edges: list[BuildingEdge]
    hazardGrid: dict


class NodeState(BaseModel):
    nodeId: str
    online: bool
    temperature: float
    smoke: float
    co: float
    flameDetected: bool
    occupants: int
    nextHop: Optional[str] = None
    failoverTier: str
    lastSeenMs: int
    sensorOk: bool


class EvacRoute(BaseModel):
    id: str
    path: list[str]
    priority: float


class NetworkStats(BaseModel):
    totalPackets: int
    packetsPerSec: float
    crcFailures: int
    staleNodes: int
    avgLatencyMs: float
    websocket: str


class Snapshot(BaseModel):
    t: int
    status: str
    scenario: str
    nodes: dict[str, NodeState]
    hazard: dict[int, list[float]]
    routes: list[EvacRoute]
    network: NetworkStats
    activeFireNodes: list[str]


class InjectRequest(BaseModel):
    nodeId: str
    scenario: str


class TimeRange(BaseModel):
    fromMs: int
    toMs: int
