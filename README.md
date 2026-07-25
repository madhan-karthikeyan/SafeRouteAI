# SafeRouteAI — Dynamic Fire Evacuation Router

Decentralized, self-healing evacuation-routing system for commercial buildings. Each ESP32 node senses local fire hazard, fuses it into a continuous exponential cost, shares it with mesh neighbors via ESP-NOW, and independently runs Dijkstra to compute the safest exit path. No central server decides a path — the dashboard is read-only telemetry.

## Repository Structure

```
fire-evac-router/
├── firmware/          # ESP32 C/C++ (PlatformIO)
│   ├── src/           # main, routing, fusion, comms, leds, failsafe, gateway
│   ├── include/       # HazardPacket, graph_topology, link_state, routing, etc.
│   └── platformio.ini
├── backend/           # FastAPI → WebSocket bridge (MQTT ↔ frontend)
│   ├── main.py        # REST + WebSocket endpoints
│   ├── mqtt_bridge.py # MQTT subscriber + Snapshot aggregation
│   ├── graph_service.py
│   ├── heatmap_service.py
│   ├── snapshot_store.py
│   └── requirements.txt
├── frontend/          # React + Vite + R3F digital twin (Lovable-generated)
│   ├── src/
│   │   ├── api/       # SafeRouteApi interface, mock, http client
│   │   ├── components/scene/  # 3D scene (Building, Nodes, Fire, Smoke, etc.)
│   │   ├── components/panels/ # NodeHealth, NetworkStats, FireInjector, etc.
│   │   └── stores/    # Zustand (useTwinStore, useUiStore)
│   └── package.json
├── simulator/         # Python digital twin / injector
│   ├── injector.py    # CLI fire injection tool
│   ├── graph_model.py # topology + calibration loader
│   ├── fire_profiles/ # slow-smolder, flashover, regression
│   └── data/          # building_graph.json
├── dashboard/         # Node-RED flow + UI
│   ├── flows.json     # Node-RED import
│   └── ui/            # floor grid, health panel, shelter panel
├── docs/              # engineering report, architecture
├── tests/             # firmware, simulator, integration tests
├── docker/            # Mosquitto + Node-RED + Backend compose
└── scripts/           # build, test, demo runners
```

## Quick Start

### Prerequisites

- PlatformIO (for firmware)
- Python 3.10+ (for injector + backend)
- Node.js 18+ or Bun (for frontend)
- Docker (for Mosquitto + Node-RED)
- ESP32 dev board (or Wokwi simulation)

### Full-Stack Demo (no hardware needed)

```bash
# 1. Install backend deps
pip install -r backend/requirements.txt

# 2. Install frontend deps
cd frontend && bun install && cd ..

# 3. Start everything
./scripts/start-demo.sh
# Frontend : http://localhost:5173  (3D digital twin)
# Backend  : http://localhost:8000  (API + WebSocket)
# API docs : http://localhost:8000/docs
```

The frontend runs in **mock mode** by default (`VITE_USE_MOCK=true`). Switch to live mode by setting `VITE_USE_MOCK=false` in `frontend/.env` — the frontend will then connect to the FastAPI backend, which bridges MQTT from the ESP32 mesh.

### Build Firmware

```bash
pio run --environment esp32dev
```

### Run Tests

```bash
./scripts/run-all-tests.sh
```

### Run Injector (CLI)

```bash
python3 simulator/injector.py --cli
# Commands: slow | flashover | zone <id> | corrupt | clean | quit
```

### Start Node-RED Dashboard

```bash
cd docker
docker-compose up -d mosquitto nodered
# Open http://localhost:1880 → Import dashboard/flows.json
```

## Architecture

### Firmware (ESP32)

```
Sensor read → dual-path conditioning → sensor fusion →
  update own link-state entry if triggered → flood via ESP-NOW →
  neighbors accept only if seq_num newer →
  local Dijkstra over double-buffered link-state table →
  shelter-in-place check → hold-down check →
  LED color/animation decision →
  gateway relays state to MQTT (best-effort, never on decision path)
```

### Full Stack

```
ESP32 Mesh ──→ MQTT Broker ──→ FastAPI ──→ WebSocket ──→ React + R3F Frontend
                    │                                    (3D Digital Twin)
                    └──→ Node-RED Dashboard
                         (legacy monitoring)
```

The frontend is a **read-only observer**. All routing, sensor fusion, and fail-safe decisions execute on the ESP32 mesh. The FastAPI backend aggregates per-node MQTT messages into unified Snapshots and pushes them via WebSocket. The frontend never computes a safety-critical path.

## Key Design Decisions

- **Double-buffered link-state table**: No mutex needed — callback writes inactive buffer, atomically swaps pointer
- **Dual-path detection**: EWMA slow path + rate-of-change fast path with 2-sample debounce
- **Continuous exponential cost**: No binary thresholds in temperature or smoke
- **Three-tier sensor fail-safe**: Local sensor → neighbor consensus → static default
- **Hold-down hysteresis**: Prevents LED flicker on small cost oscillations

## Evaluation Criteria Coverage

| Criterion | Weight | Implementation |
|---|---|---|
| Algorithm Responsiveness & Sensor Fusion | 30% | On-device Dijkstra, exponential cost, dual-path detection |
| Simulation Quality & Demonstration | 20% | Python injector, 2 fire profiles, CLI zone control |
| Visual Interface & Usability | 15% | LED chase animation, color-coded (G/Y/R/W) |
| Solution Pitch & Presentation | 15% | Engineering report with flowchart |
| Multi-Node Communication | 10% | ESP-NOW mesh, seq_num, CRC16 |
| Fail-Safe Operation | 10% | Corrupt packet, drop, sensor failure handling |
