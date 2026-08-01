# SafeRouteAI Simulation Documentation

## Overview

The simulator (`simulator/`) is a Python-based digital twin fire injection tool that generates realistic multi-sensor fire timelines. It can broadcast binary hardware packets over serial/ESP-NOW or publish telemetry payloads over MQTT. It is used for:

- **Development**: Testing the backend and frontend without live hardware
- **Demonstration**: Running pre-scripted fire scenarios for presentations
- **Hardware-in-the-loop**: Injecting sensor data into real ESP32 mesh networks
- **Calibration**: Fitting logistic growth curves to fire data

```
simulator/
├── data/
│   └── building_graph.json    # Default 6-node test topology
├── fire_profiles/
│   ├── slow_smolder.py        # Logistic growth, 25→65°C over ~60s
│   ├── flashover.py           # Near-step function, 250°C in ~5s
│   └── regression.py          # Offline logistic curve fitting
├── graph_model.py             # Topology loader and node model
├── injector.py                # CLI and MQTT injector (main entry point)
├── requirements.txt
└── README.md
```

## Fire Injector (`injector.py`)

The injector is the primary simulation tool. It can run in interactive CLI mode, single-shot packet generation mode, or automated MQTT broadcast mode.

### CLI Usage

```bash
# Interactive mode
python3 simulator/injector.py --cli

# Generate and print one packet
python3 simulator/injector.py --packet 1

# MQTT broadcast to a specific zone
python3 simulator/injector.py --mqtt --broker localhost --profile flashover --zone 3

# Single-shot with corrupt packets
python3 simulator/injector.py --corrupt --packet 5
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `slow` | Activate slow smolder fire profile (logistic growth) |
| `flashover` | Trigger fast flashover on the currently targeted zone |
| `zone <id>` | Set the target zone/node ID for fire injection |
| `corrupt` | Enable corrupt packet mode (CRC = 0x0000) |
| `clean` | Disable corrupt packet mode (normal CRC) |
| `pub` | Publish current sensor readings to MQTT broker |
| `quit` | Exit the injector CLI |

### Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--graph` | `str` | `None` | Path to building graph JSON file |
| `--cli` | `flag` | `False` | Enable interactive CLI mode |
| `--zone` | `int` | `None` | Target zone/node ID |
| `--profile` | `str` | `slow` | Fire profile: `slow` or `flashover` |
| `--corrupt` | `flag` | `False` | Enable CRC corruption on all packets |
| `--packet` | `int` | `None` | Generate one packet for this node and print |
| `--mqtt` | `flag` | `False` | Enable MQTT broadcasting |
| `--broker` | `str` | `localhost` | MQTT broker hostname |

### MQTT Publishing Mode

When `--mqtt` is used, the injector connects to a Mosquitto broker and publishes simulated sensor data on topic `evac/node/<node_id>/hazard`. The payload format matches the ESP32 hardware packet format:

```
struct hazard_packet {
    uint16_t node_id;
    uint32_t seq_num;
    uint32_t uptime_ms;
    float    temp_c;
    float    smoke_ppm;
    bool     flame_detected;
    float    edge_cost;
    uint16_t crc;         // CRC-16-IBM of preceding bytes
} __attribute__((packed));
```

Packet size: 29 bytes.

### Zone-Targeted Injection

Only the targeted zone receives elevated sensor readings from the active fire profile. All other nodes report baseline values (25°C, 0 ppm smoke, no flame). The target zone is set with `zone <id>` in CLI or `--zone` on the command line.

### Packet Corruption Injection

In corrupt mode, the CRC field is set to `0x0000` instead of the computed CRC-16-IBM value. The ESP32 mesh firmware's CRC check rejects these packets, demonstrating fail-safe behavior. The `print_packet` command shows whether the CRC is valid:

```
Packet [29b]:
  Node ID:    3
  Temp:       25.0 C
  Smoke:      0 ppm
  Flame:      False
  Edge Cost:  0.00
  CRC valid:  FALSE (stored=0x0000, computed=0xa3b1)
  Hex:        03000000...
```

## Fire Profiles

### `slow_smolder.py`

Logistic growth curve for gradual temperature rise and smoke buildup. Simulates a smoldering fire (e.g., electrical fault, trash can fire).

```python
logistic_temp = max_temp / (1 + exp(-growth_rate * (t - t_offset)))
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_temp` | 65.0°C | Temperature asymptote (above 25°C baseline) |
| `max_smoke` | 800.0 ppm | Smoke asymptote |
| `growth_rate` | 0.08 | Logistic growth constant |
| `t_offset` | 60.0s | Time at which growth is fastest |

**Behavior**: Temperature rises from 25°C to ~90°C (25 + 65) over ~60 seconds. Smoke rises from 0 to ~800 ppm. Flame detection triggers at t > 50s.

Growth curve:

```
Temp (°C)
  90 ┤                                              ╭────
     │                                         ╭────╯
  70 ┤                                   ╭────╯
     │                              ╭────╯
  50 ┤                         ╭────╯
     │                    ╭────╯
  30 ┤               ╭────╯
     │    ╭──────────╯
  25 ┤───╯
     └──────────────────────────────────────────► Time (s)
     0    10    20    30    40    50    60    70
```

### `flashover.py`

Near-step function for rapid thermal runaway. Simulates a flashover event (e.g., fuel spill ignition, rapid fire spread).

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_temp` | 250.0°C | Temperature asymptote (above 25°C baseline) |
| `max_smoke` | 3000.0 ppm | Smoke asymptote |
| `growth_rate` | 1.2 | Logistic growth constant (15× faster than smolder) |

**Behavior**: Temperature spikes from 25°C to ~275°C within ~5 seconds. Smoke spikes from 50 to ~3050 ppm. Flame detection triggers at t > 2s.

Growth curve:

```
Temp (°C)
 275 ┤                                        ╭────
     │                                    ╭────╯
 200 ┤                               ╭────╯
     │                          ╭────╯
 125 ┤                     ╭────╯
     │                 ╭────╯
  75 ┤            ╭────╯
     │        ╭────╯
  25 ┤────────╯
     └──────────────────────────────────────────► Time (s)
     0    1     2     3     4     5     6     7
```

### `regression.py`

Offline script for fitting logistic growth constants from fire time-series data. Useful for calibrating `alpha`, `beta`, and `gamma` fusion constants from Section 5.1 against real fire datasets (NIST, Kaggle).

```bash
python3 simulator/fire_profiles/regression.py
```

Without a dataset, it prints the default placeholder constants:
- `alpha` = 2.2 (temperature weight)
- `beta` = 1.6 (smoke weight)
- `gamma` = 0.5 (occupancy congestion weight)

## Building Graph Model (`graph_model.py`)

The simulator uses its own lightweight `BuildingGraph` model (not the backend's Pydantic model). It stores:

- **Nodes**: Position, floor, exit flag, calibration constants (`T_baseline`, `T_critical`, `S_baseline`, `S_critical`, `occupant_capacity`)
- **Edges**: Connectivity, base distance, occupant capacity, floor transition flag

### Default Topology

A 6-node test graph with 8 edges and 3 exits:

```
    exit-1 ◄────► node-2 ◄────► node-3 ◄────► exit-6
       ▲            ▲            ▲
       │            │            │
       │         node-5       node-4
       │            ▲            ▲
       └────────────┴────────────┘
                    │
                 exit-4
```

### Edge Cost Formula (Simulator)

The injector computes edge costs matching the firmware algorithm:

```python
T_norm = clamp((temp - T_baseline) / (T_critical - T_baseline), 0, 1)
S_norm = clamp((smoke - S_baseline) / (S_critical - S_baseline), 0, 1)
hazard_mult = exp(2.2 * T_norm + 1.6 * S_norm)
edge_cost = dist * hazard_mult + 0.5 * O_norm * dist
if flame:
    edge_cost *= 1_000_000
```

## Simulation Workflow

### 1. Select Building and Fire Profile

Choose a building (default: 6-node test graph) and a fire profile:

```bash
python3 simulator/injector.py --cli
inject> slow
```

### 2. Target Zone/Node

Identify the zone (node ID) where the fire should originate:

```bash
inject> zone 3
```

### 3. Inject Simulated Sensor Data

The injector generates realistic sensor readings based on the active profile. Readings update in real-time as the fire grows:

```bash
inject> pub
```

This broadcasts the current sensor values for the targeted zone to the MQTT broker. The backend's `mqtt_bridge.py` receives them and integrates into the simulation.

### 4. Observe System Response

The backend processes the injected data through its pipeline:

```
Injector → MQTT → mqtt_bridge → NodeState update
                                   ↓
                            heatmap recompute
                                   ↓
                            Dijkstra route compute
                                   ↓
                            Snapshot push
                                   ↓
                            WebSocket broadcast
                                   ↓
                            Frontend visualization
```

## Hardware-in-the-Loop Testing Workflow

The injector can drive real ESP32 hardware by broadcasting binary packets over serial or MQTT:

1. **Deploy firmware** to ESP32 mesh nodes
2. **Start MQTT broker**: `mosquitto -d`
3. **Start backend**: `uvicorn backend.main:app`
4. **Run injector**: `python3 simulator/injector.py --mqtt --profile flashover --zone 3`
5. **Observe**: ESP32 nodes receive the simulated hazard packets via MQTT, compute routes locally, and report back their status

This validates that:
- The mesh routing algorithm converges correctly
- Failover tiers activate on sensor/comm failure
- The MQTT bridge assembles consistent snapshots from live node reports
- The frontend renders real data identically to simulated data

## Example Scenarios

### Demo: Gradual Fire Spread

```bash
# Terminal 1: Start backend
uvicorn backend.main:app --reload

# Terminal 2: Start injector CLI
python3 simulator/injector.py --cli
inject> zone 3
inject> slow

# Wait 30 seconds for temperature to rise
inject> pub
# Temperature at node 3 should be ~55°C
```

### Demo: Flashover with Failures

```bash
# Terminal 1: Start backend
uvicorn backend.main:app --reload

# Terminal 2: Inject flashover via REST API
curl -X POST "http://localhost:8000/api/inject?buildingId=mega-mall" \
  -H "Content-Type: application/json" \
  -d '{"nodeId":"n-zone-1","scenario":"flashover"}'

# Terminal 3: Observe WebSocket stream
websocat "ws://localhost:8000/api/events?buildingId=mega-mall"
```

### Demo: Automated Sequence

```bash
# Built-in 30-second demo
curl -X POST "http://localhost:8000/api/demo?buildingId=mega-mall"
```

Starts a multi-stage demo: slow smolder → flashover → comm failures → sensor failures.

### Testing: Packet Validation

```bash
# Generate and inspect a single packet
python3 simulator/injector.py --packet 3

# Generate with corruption to test CRC rejection
python3 simulator/injector.py --corrupt --packet 3
```

### Testing: Sensor Failure

```bash
curl -X POST "http://localhost:8000/api/inject" \
  -H "Content-Type: application/json" \
  -d '{"nodeId":"n-zone-1","scenario":"sensor_failure"}'
```

Expected: The node's `sensorOk` becomes `false`, `failoverTier` becomes `"tertiary"`, and temperature/smoke readings drop to 0.

### Testing: Communication Failure

```bash
curl -X POST "http://localhost:8000/api/inject" \
  -H "Content-Type: application/json" \
  -d '{"nodeId":"n-zone-2","scenario":"comm_failure"}'
```

Expected: The node's `online` becomes `false`, `failoverTier` becomes `"isolated"`, and `lastSeenMs` ages by 2× the stale threshold.
