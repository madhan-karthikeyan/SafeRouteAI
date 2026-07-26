from pydantic import BaseModel, Field
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
    model_config = {"populate_by_name": True}
    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")


class Room(BaseModel):
    id: str
    x: float
    z: float
    width: float
    depth: float
    label: Optional[str] = None
    type: Optional[str] = None


class FloorPlanRoomSeg(BaseModel):
    model_config = {"populate_by_name": True}
    from_: tuple[float, float] = Field(alias="from")
    to: tuple[float, float]
    width: float


class FloorPlan(BaseModel):
    index: int
    name: str
    size: dict
    origin: Vec3
    rooms: list[Room]
    corridors: list[FloorPlanRoomSeg]


class BuildingGraph(BaseModel):
    id: str
    name: str
    floors: list[FloorPlan]
    nodes: list[BuildingNode]
    edges: list[BuildingEdge]
    hazardGrid: dict


class BuildingMeta(BaseModel):
    id: str
    name: str
    type: str
    description: str
    floors: int
    totalRooms: int
    totalExits: int
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    license: Optional[str] = None


class BuildingDefRoom(BaseModel):
    id: str
    label: str
    type: str
    floor: int
    x: float
    z: float
    width: float
    depth: float
    isExit: Optional[bool] = None
    isStairwell: Optional[bool] = None
    capacity: Optional[int] = None


class CorridorDef(BaseModel):
    id: str
    fromRoom: str
    toRoom: str
    floor: int
    width: float
    junctionPoints: Optional[list[Vec3]] = None
    isStairwell: Optional[bool] = None


class BuildingDefFloor(BaseModel):
    index: int
    name: str
    elevation: float
    width: float
    depth: float


class BuildingDef(BaseModel):
    meta: BuildingMeta
    rooms: list[BuildingDefRoom]
    corridors: list[CorridorDef]
    floors: list[BuildingDefFloor]


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
    hazard: dict[str, list[float]]
    routes: list[EvacRoute]
    network: NetworkStats
    activeFireNodes: list[str]


class InjectRequest(BaseModel):
    nodeId: str
    scenario: str


class TimeRange(BaseModel):
    fromMs: int
    toMs: int
