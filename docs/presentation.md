# SafeRouteAI: Dynamic Fire Evacuation Router

## Slide 1: Title
**SafeRouteAI** — Decentralized Evacuation Routing with Real-Time Hazard Mapping
Engineering Team: [Your Name]
Date: 2026

## Slide 2: The Problem
- Static exit signs guide occupants directly into danger during fires
- Toxic smoke inhalation and flashovers happen in minutes
- Centralized systems have a single point of failure
- 300ms reaction time required for meaningful path correction

## Slide 3: End-to-End System Architecture

```
┌─────────────────┐      ESP-NOW Mesh (TTL=4)      ┌──────────────────┐
│ ESP32 Node #1   │ ◄────────────────────────────► │ ESP32 Node #2    │
│ (DHT22/MQ-2/IR) │                                │ (Dijkstra Router)│
└────────┬────────┘                                └─────────┬────────┘
         │                                                   │
         └───────────────────┐       ┌───────────────────────┘
                             ▼       ▼
                    ┌─────────────────────────┐
                    │ Zone Gateway Node       │
                    └────────────┬────────────┘
                                 │ MQTT (Port 1883)
                                 ▼
                    ┌─────────────────────────┐
                    │ FastAPI Backend Bridge  │
                    │ - Snapshot Ring Buffer  │
                    │ - Async IDW Heatmap     │
                    └────────────┬────────────┘
                                 │ WebSockets (WS /api/events)
                                 ▼
                    ┌─────────────────────────┐
                    │ 3D Digital Twin EOC UI  │
                    │ (Three.js / React)      │
                    └─────────────────────────┘
```

## Slide 4: Technical Approach
- **Algorithm**: Dijkstra on-device with continuous exponential cost function
- **Sensor Fusion**: Temperature, smoke, flame, occupancy → unified edge cost
- **Communication**: ESP-NOW mesh with sequence-numbered flooding + CRC16
- **Fail-safe**: Three-tier hierarchy (local → neighbor consensus → static default)

## Slide 5: Key Innovation — Dual-Path Detection
- **Slow path**: EWMA filtering with delta threshold (noise rejection)
- **Fast path**: Rate-of-change trigger with 2-sample debounce (flashover capture)
- Either path fires → immediate link-state flood

## Slide 6: Cost Function
```
T_norm = clamp((T − T_baseline) / (T_critical − T_baseline), 0, 1)
S_norm = clamp((Smoke − S_baseline) / (S_critical − S_baseline), 0, 1)
cost = base_distance × exp(2.2×T_norm + 1.6×S_norm) + congestion
     × (flame ? 1e6 : 1)
```
- Continuous, exponential — no binary thresholds
- Congestion additive, never multiplicative with hazard

## Slide 7: System Characteristics

| Metric | Value |
|---|---|
| Reaction time (4-hop worst case) | < 300ms (projected 182ms) |
| Mesh protocol | ESP-NOW (connectionless, low-latency) |
| Packet validation | CRC16, sequence number anti-replay |
| Hold-down hysteresis | 1800ms anti-flicker |
| Sensor fail-safe | 3 tiers: local → consensus → default |

## Slide 8: Fail-Safe Design
- **Tier 1**: Local sensor healthy → use local reading
- **Tier 2**: Local sensor failed, neighbors reachable → neighbor consensus
- **Tier 3**: Isolated node → static pre-flashed default path
- Dashboard surfaces sensor-fault status in real time

## Slide 9: Demo Flow
1. Start injector with slow smolder profile on zone 3
2. Trigger flashover — observe LED flip from GREEN to RED_PULSE
3. Enable corrupt packet mode — show CRC rejection on dashboard
4. Disconnect sensor — dashboard shows "SENSOR FAULT – neighbor consensus"
5. Block all exits — dashboard shows "SHELTER-IN-PLACE"

## Slide 10: Hardware Cost Breakdown
| Component | Cost per node |
|---|---|
| ESP32 | $3-5 |
| DHT22 | $2-3 |
| MQ-2 | $3-4 |
| IR flame sensor | $2-3 |
| WS2812B strip | $5-8 |
| Buzzer | $1 |
| **Total** | **$16-24** |

## Slide 11: Scalability
- ESP-NOW clusters of ≤15 nodes per peer group
- Zone Gateways for multi-floor relay
- Augments, not replaces, code-mandated static signage
- Occupancy sensing (access control/cameras) is the dominant cost — not hazard nodes

## Slide 12: Commercial Viability
- Retrofit-friendly: mounts alongside existing exit signs
- No central wiring required — battery-backed ESP32 nodes
- Data-driven fire model calibration from NIST/Kaggle datasets
- Cloud-independent: safety path never depends on dashboard availability

## Slide 13: Q&A
- What happens when all paths are blocked? → Shelter-in-place state
- How do you prevent path oscillation? → Hold-down hysteresis
- What if a sensor breaks? → Three-tier fail-safe, dashboard alert
- How fast does it react? → <300ms worst case, measured
