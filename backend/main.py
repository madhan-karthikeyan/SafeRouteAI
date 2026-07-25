"""
FastAPI application — bridges MQTT mesh to WebSocket frontend.

Endpoints:
  GET  /api/graph      → BuildingGraph topology
  WS   /api/events     → Snapshot stream (WebSocket)
  POST /api/inject     → Trigger fire/sensor/comm event
  POST /api/reset      → Clear all events
  POST /api/demo       → Run auto-demo sequence
  GET  /api/replay     → Historical snapshots
"""

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import Snapshot, InjectRequest, TimeRange
from .graph_service import load_graph
from .snapshot_store import SnapshotStore
from .mqtt_bridge import MqttBridge

store = SnapshotStore()
bridge = MqttBridge(store)
graph = load_graph()

_ws_connections: list[WebSocket] = []
_tick_task: asyncio.Task | None = None
_demo_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bridge.start()
    global _tick_task
    _tick_task = asyncio.create_task(_tick_loop())
    yield
    if _tick_task:
        _tick_task.cancel()
    bridge.stop()


app = FastAPI(title="SafeRouteAI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _tick_loop():
    while True:
        bridge.tick()
        snap = store.latest()
        if snap:
            dead: list[WebSocket] = []
            for ws in _ws_connections:
                try:
                    await ws.send_json(_snapshot_to_dict(snap))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in _ws_connections:
                    _ws_connections.remove(ws)
        await asyncio.sleep(0.2)


def _snapshot_to_dict(snap: Snapshot) -> dict:
    d = snap.model_dump()
    d["hazard"] = {str(k): v for k, v in d["hazard"].items()}
    return d


# ── REST endpoints ────────────────────────────────────────────────


@app.get("/api/graph")
async def get_graph():
    return JSONResponse(json.loads(graph.model_dump_json()))


@app.post("/api/inject")
async def inject(req: InjectRequest):
    bridge.inject(req.nodeId, req.scenario)
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    return {"ok": True}


@app.post("/api/reset")
async def reset():
    global _demo_task
    bridge.reset()
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    return {"ok": True}


@app.post("/api/demo")
async def run_demo():
    global _demo_task
    bridge.reset()
    if _demo_task and not _demo_task.done():
        _demo_task.cancel()
    _demo_task = asyncio.create_task(_auto_demo())
    return {"ok": True}


async def _auto_demo():
    stages = [
        (0, lambda: None),
        (2, lambda: bridge.inject("n-1-1-3", "slow_smolder")),
        (5, lambda: bridge.inject("n-1-1-3", "slow_smolder")),
        (10, lambda: bridge.inject("n-1-2-4", "flashover")),
        (15, lambda: (
            bridge.inject("n-1-0-5", "comm_failure"),
            bridge.inject("n-1-1-5", "comm_failure"),
            bridge.inject("n-1-2-5", "comm_failure"),
        )),
        (20, lambda: (
            bridge.inject("n-2-1-1", "sensor_failure"),
            bridge.inject("n-2-2-2", "sensor_failure"),
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


@app.get("/api/replay")
async def get_replay(from_ms: int = 0, to_ms: int = 0):
    if to_ms == 0:
        to_ms = int(time.time() * 1000)
    snapshots = store.get_range(from_ms, to_ms)
    return JSONResponse([_snapshot_to_dict(s) for s in snapshots])


# ── WebSocket ──────────────────────────────────────────────────────


@app.websocket("/api/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
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
                    bridge.inject(data["inject"]["nodeId"], data["inject"]["scenario"])
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)
