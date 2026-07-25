# SafeRouteAI — Dynamic Fire Evacuation Router

Decentralized, self-healing evacuation-routing system for commercial buildings. Each ESP32 node senses local fire hazard, fuses it into a continuous exponential cost, shares it with mesh neighbors via ESP-NOW, and independently runs Dijkstra to compute the safest exit path. No central server decides a path — the dashboard is read-only telemetry.

## Repository Structure

```
fire-evac-router/
├── firmware/          # ESP32 C/C++ (PlatformIO)
│   ├── src/           # main, routing, fusion, comms, leds, failsafe, gateway
│   ├── include/       # HazardPacket, graph_topology, link_state, routing, etc.
│   └── platformio.ini
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
├── docker/            # Mosquitto + Node-RED compose
└── scripts/           # build, test, demo runners
```

## Quick Start

### Prerequisites

- PlatformIO (for firmware)
- Python 3.10+ (for injector)
- Docker (for dashboard)
- ESP32 dev board (or Wokwi simulation)

### Build Firmware

```bash
cd firmware
pio run --environment esp32dev
```

### Flash to Device

```bash
pio run --environment esp32dev -t upload
```

### Run Injector (CLI)

```bash
python3 simulator/injector.py --cli

# Commands: slow | flashover | zone <id> | corrupt | clean | quit
```

### Generate a Test Packet

```bash
python3 simulator/injector.py --zone 3 --profile flashover --packet 2
```

### Run Tests

```bash
./scripts/run-all-tests.sh
```

### Start Dashboard

```bash
cd docker
docker-compose up -d
# Open http://localhost:1880
# Import dashboard/flows.json
```

## Architecture

```
Sensor read → dual-path conditioning → sensor fusion →
  update own link-state entry if triggered → flood via ESP-NOW →
  neighbors accept only if seq_num newer →
  local Dijkstra over double-buffered link-state table →
  shelter-in-place check → hold-down check →
  LED color/animation decision →
  gateway relays state to MQTT (best-effort, never on decision path)
```

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
