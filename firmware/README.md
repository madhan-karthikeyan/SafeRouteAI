# SafeRouteAI — Firmware Documentation

Modular C/C++ firmware designed for ESP32 microcontrollers using PlatformIO and Arduino framework.

## Architecture

The firmware operates as a link-state router for localized fire hazards. Each node continuously senses environmental inputs, calculates continuous exponential edge weights, floods updates via ESP-NOW, and computes shortest evacuation paths using an on-device Dijkstra algorithm.

```
Sensors (DHT22, MQ-2, IR) → Dual-Path Conditioning (EWMA + Rate Trigger)
   ↓
Continuous Sensor Fusion → Edge Cost Formula
   ↓
Double-Buffered Link-State Table (Atomic Pointer Swap)
   ↓
On-Device Dijkstra Path Planner + Hold-Down Hysteresis
   ↓
FastLED Animation Controller (FreeRTOS Task) + Local Buzzer
   ↓
ESP-NOW Mesh Flooding (Seq-Num Anti-Replay + CRC16 Validation)
   ↓
Gateway Relay → MQTT Telemetry (Read-only)
```

## Directory Structure

```
firmware/
├── include/
│   ├── comms.h          # ESP-NOW mesh networking & packet flooding
│   ├── failsafe.h       # 3-tier sensor health monitoring & consensus
│   ├── fusion.h         # Continuous exponential sensor fusion math
│   ├── gateway.h        # MQTT bridge relay interface
│   ├── graph_topology.h # Building graph definitions & neighbor adjacency
│   ├── HazardPacket.h   # Wire packet layout with CRC16 checksum
│   ├── leds.h           # WS2812B FastLED animation interface
│   ├── link_state.h     # Double-buffered link state table
│   ├── routing.h        # Dijkstra pathfinder & shelter-in-place detector
│   └── sensor_drivers.h # Physical sensor pin reads (DHT22, MQ-2, IR flame)
├── src/
│   ├── comms.cpp        # ESP-NOW packet routing & sequence check
│   ├── failsafe.cpp     # Sensor health variance & noise floor checks
│   ├── fusion.cpp       # Continuous exponential cost calculation
│   ├── gateway.cpp      # Wi-Fi / MQTT gateway publisher
│   ├── HazardPacket.cpp # CRC16 calculation & validation
│   ├── leds.cpp         # FreeRTOS LED chase/strobe task
│   ├── link_state.cpp   # Link state memory management
│   ├── main.cpp         # System setup, control loop, task dispatcher
│   ├── routing.cpp      # Priority queue Dijkstra implementation
│   └── sensor_drivers.cpp # Analog/digital sensor sampling
└── README.md
```

## Key Components

### 1. Sensor Manager & Fusion (`fusion.cpp`, `sensor_drivers.cpp`)
- Evaluates ambient temperature (°C), smoke concentration (PPM), flame detection (Boolean), and corridor occupancy.
- Cost formula:
  `cost = base_distance * exp(2.2 * T_norm + 1.6 * S_norm) + 0.5 * O_norm * base_distance * (flame ? 1e6 : 1)`
- Dual-Path Detection: EWMA slow path for noise rejection; rate-of-change fast path with 2-sample debounce for instant flashover response.

### 2. Path Planner & Decision Logic (`routing.cpp`)
- Runs Dijkstra's algorithm directly on the ESP32.
- Enters `SHELTER-IN-PLACE` state if all exits are blocked by flame (`cost >= 100,000`).
- Prevents oscillation via hold-down timer (`1800ms`).

### 3. LED Controller (`leds.cpp`)
- Runs as a dedicated FreeRTOS task on Core 1 to ensure smooth visual guidance without blocking pathfinding.
- Visual States:
  - **Green Chase**: Safe evacuation path.
  - **Yellow Chase**: High-smoke alternate route.
  - **Red Pulse**: Immediate danger / hazard area.
  - **White Strobe**: Shelter-in-place mode.

### 4. Communication Layer (`comms.cpp`, `HazardPacket.cpp`)
- Peer-to-peer connectionless ESP-NOW broadcast (sub-10ms per hop).
- Validated with CRC16 checksums and sequence counter anti-replay protection.

### 5. Sensor Fail-Safe Manager (`failsafe.cpp`)
- Tier 1: Local sensor healthy → use local readings.
- Tier 2: Local sensor faulty → use neighbor consensus estimate.
- Tier 3: Isolated node → fall back to static default pre-flashed path.

## Build Instructions

Using PlatformIO CLI:

```bash
# Build firmware binary
pio run --environment esp32dev

# Upload to ESP32 board
pio run --target upload --environment esp32dev

# Open Serial Monitor (115200 baud)
pio device monitor
```

Using VS Code with PlatformIO IDE extension:
1. Open root folder `/home/madhan/Documents/PlatformIO/Projects/SafeRouteAI` in VS Code.
2. Click **Build** or **Upload** in the PlatformIO toolbar.
