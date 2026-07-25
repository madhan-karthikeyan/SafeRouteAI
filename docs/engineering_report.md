# Engineering Report: Dynamic Fire Evacuation Router

## 1. System Overview

SafeRouteAI is a decentralized, self-healing evacuation-routing system for commercial buildings. Each ESP32 node acts as a link-state router for physical hazard, continuously sensing temperature, smoke, flame, and occupancy, fusing them into a continuous exponential edge cost, and running Dijkstra to compute the safest path to an exit. The mesh uses ESP-NOW for low-latency node-to-node communication with sequence-numbered flooding and CRC16 validation.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Node Architecture                        │
│                                                                 │
│  Sensors → Dual-Path Detection → Sensor Fusion → Cost Formula  │
│                ↓                                                │
│         Link-State Table (double-buffered)                      │
│                ↓                                                │
│         Local Dijkstra → Hold-Down → LED Decision               │
│                ↓                                                │
│         ESP-NOW Flood (event + periodic)                        │
│                ↓                                                │
│         Gateway → MQTT → Dashboard (read-only)                  │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Sensor Fusion & Edge-Weight Calculation

### Cost Formula

The edge cost for traversing a hallway segment combines four sensor vectors:

```
T_norm = clamp((T_current - T_baseline) / (T_critical - T_baseline), 0, 1)
S_norm = clamp((Smoke_ppm - S_baseline) / (S_critical - S_baseline), 0, 1)
O_norm = clamp(occupant_count / occupant_capacity, 0, 1)

hazard_multiplier = exp(2.2 * T_norm + 1.6 * S_norm)
congestion_term    = 0.5 * O_norm * base_distance

edge_cost = (base_distance * hazard_multiplier + congestion_term)
            * (FLAME_DETECTED ? 1e6 : 1)
```

### Dual-Path Detection

Two independent conditioning paths per sensor:
- **Slow path (EWMA)**: α=0.3 exponential moving average with absolute-value delta threshold gate
- **Fast path (rate-of-change)**: Independent rate trigger with 2-consecutive-sample debounce to reject ADC glitches

Either path firing triggers a link-state update flood.

## 4. Fail-Safe Hierarchy

```
                    ┌─────────────────────────────────────┐
                    │       Local Sensor Reading          │
                    └─────────────────────────────────────┘
                                  │
                          ┌───────┴───────┐
                          │               │
                    healthy?          unhealthy?
                          │               │
                    ┌─────┘               └─────┐
                    │                           │
              Tier 1 Use                 Neighbors
              Local Value                reachable?
                                           │
                                     ┌─────┴─────┐
                                     │           │
                                    Yes          No
                                     │           │
                               Tier 2        Tier 3
                               Neighbor      Static
                               Consensus     Default
```

Three tiers of fallback, mirroring the local-first design with the necessary inversion for sensor failure — a node only trusts neighbors over itself when its own sensor is *provably* implausible.

## 5. Key Protocol Details

### HazardPacket (24 bytes on wire)

| Field | Type | Size |
|---|---|---|
| node_id | uint16_t | 2B |
| seq_num | uint32_t | 4B |
| node_uptime_ms | uint32_t | 4B |
| temp_c | float | 4B |
| smoke_ppm | float | 4B |
| flame_detected | bool | 1B |
| edge_cost | float | 4B |
| crc16 | uint16_t | 2B |

### Timing Budget (projected)

| Stage | p95 | Worst-case |
|---|---|---|
| Sensor read + fusion | 6ms | 8ms |
| Threshold check | 1ms | 1ms |
| Dijkstra recompute | 18ms | 25ms |
| ESP-NOW per hop | 15ms | 35ms |
| LED update | 6ms | 8ms |
| **4-hop total** | **91ms** | **182ms** |

## 6. LED Color Decision Logic

```
if any edge has flame → RED_PULSE
if cost >= SHELTER_THRESHOLD → WHITE_STROBE
if rerouted:
    if smoke_norm > temp_norm → YELLOW
    else → RED_PULSE
else → GREEN
```

Chase animation direction reverses by flipping the scroll increment sign. Pulse rate scales with hazard severity.

## 7. Real-World Scalability

### Hardware Cost (per node)
- ESP32: $3-5
- DHT22: $2-3
- MQ-2: $3-4
- IR flame sensor: $2-3
- WS2812B strip (30cm): $5-8
- Buzzer: $1
- **Total per node**: $16-24

### Occupancy Sensing Infrastructure
- Access control sensors at doorways/junctions: $50-200 per point
- Camera-based counting: $100-500 per camera
- Occupancy is the dominant infrastructure cost; the hazard-node hardware is negligible by comparison

### Mesh Scaling
- ESP-NOW practical limit: ~15 nodes per peer group
- Multi-floor: Zone Gateway nodes per floor relay condensed summaries cross-floor
- Building-wide: hierarchical clustering with gateway relays

### Relationship to Code-Mandated Static Signage
SafeRouteAI augments, not replaces, code-mandated static exit signage. Static signs provide always-on egress direction; the dynamic overlay adds real-time hazard avoidance. This is the correct regulatory framing for commercial deployment.

## 8. Appendix: Flowchart of Sensor Threshold → Edge Weight

```
Temperature Sensor → T_raw
                     ├─ EWMA filter → |Δ| ≥ δ_T? ─┐
                     └─ Rate |dT/dt| ≥ ρ_T? (×2) ─┤
                                                  ├─→ Trigger
Smoke Sensor → S_raw                               │
               ├─ EWMA filter → |Δ| ≥ δ_S? ───────┘
               └─ Rate |dS/dt| ≥ ρ_S? (×2) ───────┘
                                                    │
Flame Sensor → flame_IR → Boolean                  │
                                                    │
Occupancy → access_count → O_norm = occ/capacity    │
                                                    ↓
                              ┌─────────────────────────────────┐
                              │  Compute Edge Cost             │
                              │  T_norm = clamp(T_raw...)      │
                              │  S_norm = clamp(S_raw...)      │
                              │  hazard = exp(αT + βS)         │
                              │  cost = base × hazard + γO     │
                              │  if flame: cost *= BLOCK_MULT  │
                              └─────────────────────────────────┘
                                                    │
                                                    ↓
                              ┌─────────────────────────────────┐
                              │  Dijkstra over link-state table │
                              │  Output: next_hop, cost_to_exit│
                              └─────────────────────────────────┘
                                                    │
                                              ┌─────┴─────┐
                                              │           │
                                        cost≥1e5?     cost<1e5?
                                              │           │
                                      WHITE_STROBE     GREEN/YELLOW/RED
                                      (shelter)        per decision logic
```
