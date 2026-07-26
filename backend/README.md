# SafeRouteAI — Backend Service

FastAPI-based async service and WebSocket bridge connecting the ESP32 hardware mesh (via MQTT) to the 3D Digital Twin visualizer and Node-RED emergency dashboard.

## Overview

The backend acts as an observability bridge and digital twin state manager. It aggregates MQTT node packets from Mosquitto, computes real-time 2D spatial heatmaps via Inverse Distance Weighting (IDW) interpolation, stores snapshot history for replay, and streams updates via WebSockets.

> **Note**: The backend is **read-only telemetry**. All evacuation pathfinding and safety decisions occur entirely on-device on the ESP32 mesh nodes.

## Features

- **Multi-Building Support**: Serves graph topologies and building definitions for 5 commercial layouts:
  - `mega-mall` (default)
  - `city-hospital`
  - `office-tower`
  - `university-block`
  - `airport-terminal`
- **Real-Time WebSockets**: Pushes snapshot updates (`Snapshot` model) every 200ms (`/api/events`).
- **MQTT Bridge**: Connects to Mosquitto (`evac/node/+/hazard` and `evac/node/+/status`).
- **Heatmap Interpolation**: 2D grid diffusion and IDW hazard calculation per floor.
- **Replay Store**: In-memory ring buffer for historical snapshot querying (`/api/replay`).

## API Endpoints

- `GET /api/health` — System health and active connections.
- `GET /api/buildings` — List all available building models.
- `GET /api/graph?buildingId=...` — Retrieve graph topology JSON.
- `POST /api/inject` — Inject synthetic fire/failure scenario.
- `POST /api/reset` — Reset active building simulation state.
- `POST /api/demo` — Execute automated 30s demonstration sequence.
- `GET /api/replay?fromMs=...&toMs=...` — Historical snapshot replay.
- `WS /api/events?buildingId=...` — Real-time WebSocket snapshot stream.

## Running locally

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start backend with uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
