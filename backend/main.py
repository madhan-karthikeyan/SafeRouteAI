"""
FastAPI application — multi-building aware.

Endpoints:
  GET  /api/buildings   → List available building metadata
  GET  /api/graph       → BuildingGraph topology (optional ?buildingId=)
  WS   /api/events      → Snapshot stream (?buildingId= query param)
  POST /api/inject      → Trigger fire/sensor/comm event
  POST /api/reset       → Clear all events
  POST /api/demo        → Run auto-demo sequence
  GET  /api/replay      → Historical snapshots
"""

import asyncio
import json
import logging
import threading
import time
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import Snapshot, InjectRequest, TimeRange
from .graph_service import load_graph, list_buildings
from .engine import SimState, tick_sim, inject_hazard, reset_sim
from .snapshot_store import SnapshotStore

# Per-building state
_building_states: dict[str, SimState] = {}
_building_stores: dict[str, SnapshotStore] = {}
_ws_connections: dict[str, list[WebSocket]] = {}
_tick_task: asyncio.Task | None = None
_demo_task: asyncio.Task | None = None


def _get_state(building_id: str) -> SimState:
    if building_id not in _building_states:
        _building_states[building_id] = SimState(building_id)
    return _building_states[building_id]


def _get_store(building_id: str) -> SnapshotStore:
    if building_id not in _building_stores:
        _building_stores[building_id] = SnapshotStore()
    return _building_stores[building_id]


async def _tick_loop():
    while True:
        for bid, sim in _building_states.items():
            snap = tick_sim(sim)
            store = _get_store(bid)
            store.push(snap)

            connections = _ws_connections.get(bid, [])
            dead: list[WebSocket] = []
            for ws in connections:
                try:
                    await ws.send_json(_snapshot_to_dict(snap))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in connections:
                    connections.remove(ws)

        await asyncio.sleep(0.2)


def _snapshot_to_dict(snap: Snapshot) -> dict:
    d = snap.model_dump(by_alias=True)
    d["hazard"] = {str(k): v for k, v in d["hazard"].items()}
    return d


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _tick_task
    _tick_task = asyncio.create_task(_tick_loop())
    yield
    if _tick_task:
        _tick_task.cancel()
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()


app = FastAPI(title="SafeRouteAI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints ────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "buildings": len(_building_states),
        "ws_connections": sum(len(c) for c in _ws_connections.values()),
        "tick_running": _tick_task is not None and not _tick_task.done(),
    }


@app.get("/api/buildings")
async def get_buildings():
    buildings = list_buildings()
    return JSONResponse([b.model_dump() for b in buildings])


@app.get("/api/graph")
async def get_graph(buildingId: str | None = Query(None)):
    g = load_graph(buildingId)
    return JSONResponse(json.loads(g.model_dump_json(by_alias=True)))


@app.post("/api/inject")
async def inject(req: InjectRequest, buildingId: str | None = Query(None)):
    bid = buildingId or "mega-mall"
    sim = _get_state(bid)
    inject_hazard(sim, req.nodeId, req.scenario)
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    return {"ok": True}


@app.post("/api/reset")
async def reset(buildingId: str | None = Query(None)):
    global _demo_task
    bid = buildingId or "mega-mall"
    sim = _get_state(bid)
    reset_sim(sim)
    _get_store(bid).clear()
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    return {"ok": True}


@app.post("/api/demo")
async def run_demo(buildingId: str | None = Query(None)):
    global _demo_task
    bid = buildingId or "mega-mall"
    sim = _get_state(bid)
    reset_sim(sim)
    _get_store(bid).clear()
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    _demo_task = asyncio.create_task(_auto_demo(bid))
    return {"ok": True}


async def _auto_demo(building_id: str):
    sim = _get_state(building_id)
    stages = [
        (0, lambda: None),
        (2, lambda: _auto_inject(sim, "slow_smolder")),
        (5, lambda: _auto_inject(sim, "slow_smolder")),
        (10, lambda: _auto_inject(sim, "flashover")),
        (15, lambda: (
            _auto_inject(sim, "comm_failure"),
            _auto_inject(sim, "comm_failure"),
            _auto_inject(sim, "comm_failure"),
        )),
        (20, lambda: (
            _auto_inject(sim, "sensor_failure"),
            _auto_inject(sim, "sensor_failure"),
        )),
    ]
    start = time.time()
    stage_idx = 0
    while stage_idx < len(stages):
        elapsed = time.time() - start
        if elapsed >= stages[stage_idx][0]:
            stages[stage_idx][1]()
            stage_idx += 1
        await asyncio.sleep(0.1)


def _auto_inject(sim, scenario: str):
    nodes = [n for n in sim.graph.nodes if n.kind == "sensor" and n.floor > 0]
    if nodes:
        n = nodes[len(sim.fire_origins) % len(nodes)]
        inject_hazard(sim, n.id, scenario)


@app.get("/api/replay")
async def get_replay(from_ms: int = 0, to_ms: int = 0, buildingId: str | None = Query(None)):
    if to_ms == 0:
        to_ms = int(time.time() * 1000)
    bid = buildingId or "mega-mall"
    store = _get_store(bid)
    snapshots = store.get_range(from_ms, to_ms)
    return JSONResponse([_snapshot_to_dict(s) for s in snapshots])


# ── WebSocket ──────────────────────────────────────────────────────


@app.websocket("/api/events")
async def ws_events(websocket: WebSocket, buildingId: str | None = Query(None)):
    await websocket.accept()
    bid = buildingId or "mega-mall"
    if bid not in _ws_connections:
        _ws_connections[bid] = []
    _ws_connections[bid].append(websocket)

    sim = _get_state(bid)
    store = _get_store(bid)
    snap = store.latest()
    if snap:
        try:
            await websocket.send_json(_snapshot_to_dict(snap))
        except Exception:
            pass

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if "inject" in data:
                    inject_hazard(sim, data["inject"]["nodeId"], data["inject"]["scenario"])
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        connections = _ws_connections.get(bid, [])
        if websocket in connections:
            connections.remove(websocket)
