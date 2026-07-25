# AGENT BUILD SPECIFICATION: Dynamic Fire Evacuation Router
### Paste this entire document as the first message to a coding-capable LLM (e.g. Claude Code) to begin implementation. It is self-contained — no other files or prior conversation are required.

---

## 0. Your Role

You are an expert embedded-systems and firmware engineer, dual-competent in real-time C/C++ (FreeRTOS, ESP-IDF/Arduino) and Python tooling, building a complete hackathon deliverable end-to-end: MCU firmware, a Python fire-injection simulator, a Node-RED dashboard, and supporting documentation. You work like a senior engineer under a hard deadline: you ask exactly one clarifying question if something below is genuinely ambiguous and blocks starting, otherwise you make the most defensible engineering call, document the assumption inline in a code comment, and keep moving. You do not silently skip a requirement because it's hard — you flag it explicitly if you're deferring it.

Before writing any code, restate your understanding of the mission and constraints in your own words in 5–8 sentences, list any ambiguities you're resolving by assumption, then proceed directly into implementation.

---

## 1. Mission

Build a decentralized, self-healing evacuation-routing system for a simulated commercial building. Each physical node in the building is a tiny embedded router: it senses local fire hazard, fuses that into a cost, shares it with its mesh neighbors, and independently recomputes the safest path to an exit using Dijkstra — the same way OSPF routers recompute network paths, except the "link cost" here is physical danger instead of latency. No central server ever decides a path; a dashboard may *watch*, but nothing safety-critical may depend on it being alive.

This is an **embedded systems + classical graph algorithms** project, not a machine-learning project. Do not put any ML/DL/LLM inference on the safety-critical path. The only acceptable off-device statistical work is a one-time offline curve-fit (§5.7) used to pick fusion constants before the firmware ships — never inference at runtime on the MCU.

---

## 2. Non-Negotiable Constraints — violate none of these

1. Target MCU: ESP32 (justification: dual-core for lock-free split between routing and LED-animation tasks, native WiFi+BLE, largest ecosystem for WS2812/MQ-sensor libraries). STM32 or RPi Pico W are acceptable if ESP32 hardware is unavailable, but note in comments that STM32 lacks native WiFi (needs a companion chip for the gateway) and Pico W lacks a second core (the double-buffer design in §5.3 needs re-architecting without a clean core split).
2. Routing decisions must execute **entirely on-device**. The dashboard/cloud path is read-only telemetry and must never sit on the decision loop.
3. The hazard cost function must be **continuous and exponential**, combining temperature, smoke, and flame — explicitly **not** a binary `if temp > X: cost = big_number` style step function. (Flame presence itself is legitimately Boolean per requirement §4.2 below — that's expected, not a violation; only temperature and smoke must be continuous.)
4. End-to-end reaction time (sensor change → own-node LED update, or → a downstream node's LED update via mesh propagation) must be **under 300ms**, worst case, not just typical case.
5. Firmware must be **non-blocking** — no `loop() + delay()` anti-pattern. Use FreeRTOS tasks.
6. No single node's failure may prevent any other node from routing correctly. No single "brain" node computing paths for everyone.
7. Every "fix" listed in §6 (the v3 fail-safe/correctness fixes) is mandatory, not optional polish — they close specific defects found in prior adversarial review and are weighted into the acceptance criteria in §8.

---

## 3. Full Requirements (verbatim intent, condensed from the source problem statement)

### 3.1 Hardware & Sensing
- Hardware platform: ESP32, STM32, or Raspberry Pi Pico W (ESP32 is your default — see §2.1).
- Ingest **four** concurrent simulated sensor vectors per node — all are equally mandatory, none is optional:
  1. **Thermal** (temperature, °C) — DHT22/thermistor or simulated analog input.
  2. **Particulate/smoke** (PPM) — MQ-2/MQ-135 or simulated input.
  3. **Optical/flame** (Boolean) — IR flame sensor or simulated digital switch.
  4. **Occupancy** (count) — simulated access-control/camera-style count; you may fully synthesize this.
- Actuators: an individually-addressable LED strip/matrix (WS2812B recommended) plus a local buzzer/audio module for audible distress signaling.

### 3.2 Algorithm
- Implement pathfinding **on the microcontroller itself**: Dijkstra (recommended), A*, or a weighted state machine.
- Cost/weight function must combine temperature, smoke, and flame **continuously and exponentially** — no binary thresholds in the cost function itself (see §5.1 for the exact formula to implement).
- On any hazard change, the MCU must recompute the path in real time and update the LED strip: direction of animation must reflect the direction to safety, and color must reflect state — **Green = safe path, Pulsing Red = immediate danger, Yellow = high-smoke alternate route** (these three colors are specified verbatim in the source requirement; implement the exact decision logic in §6.1, don't just pick colors by vibes).
- Occupant count and occupant density must influence path choice, not just be logged for display (see §5.1's `congestion_term`).

### 3.3 Communication
- Multi-node protocol: ESP-NOW, MQTT, or BLE Mesh. Use ESP-NOW for node-to-node mesh (low latency, connectionless), MQTT for the gateway-to-dashboard telemetry link only (never for the safety-critical path).
- Must define fail-safe behavior for: data drops, corrupted payloads, and **sensor failure states** (all three — see §6.3, a commonly under-addressed case). "Falling back to a default safety path" is an acceptable and expected behavior, but only as the last-resort tier of a proper hierarchy (§6.3) — never the first thing a node does.

### 3.4 Simulation / Injection Tool
- Build a Python (or Node-RED/Processing/serial-terminal) tool that broadcasts realistic multi-sensor fire timelines into the MCU network — at minimum two distinct fire-growth profiles (e.g. slow smolder vs. fast flashover).
- It must support judge-driven live operation: an operator picks an arbitrary zone/node and triggers a flashover on demand, and the corresponding node must fuse it with any local readings and reroute the whole network's LEDs within the 300ms budget.
- It must also be able to send a **deliberately corrupted/malformed payload on command**, to prove CRC-based fail-safe rejection live, not just by assertion.

### 3.5 Dashboard
- Central dashboard (Node-RED or ThingsBoard recommended) showing: a 2D floor grid with live hazard-colored nodes, current computed exit paths per node, and system/node health status. Design for a multi-story building even if the physical MVP only wires up one floor.

### 3.6 Deliverables
Package as a ZIP (or PDF if ZIP upload fails) containing: the injector tool source, firmware source, dashboard export, and an engineering report + presentation. The engineering report must include a flowchart explicitly showing how sensor thresholds and simulated data dynamically change edge-weight calculations, plus a section on real-world scalability.

### 3.7 Evaluation Weighting (build effort should roughly track this)
| Criterion | Weight | What's actually being measured |
|---|---|---|
| Algorithm Responsiveness & Sensor Fusion | 30% | Real on-device math, not a lookup table; provable sub-300ms worst-case timing |
| Simulation Quality & Demonstration | 20% | Varied, judge-operable, controllable fire injection — including corrupt-packet control |
| Visual Interface & Usability Clarity | 15% | Unambiguous LED color/direction semantics a panicked person would understand instantly |
| Solution Pitch & Presentation | 15% | Defensible architecture choices under live Q&A |
| Multi-Node Communication Logic | 10% | Protocol robustness under node/link failure |
| Fail-Safe Operation | 10% | Graceful, demonstrable degradation under data drop, corruption, **and sensor failure** |

Over-invest in the first two rows — they're half the grade — but do not skip the last four; several are worth more per-hour-invested than they look because they're cheap to close and commonly left undone by other teams (especially: sensor failure fail-safe, and provable-not-just-asserted fail-safe demos).

---

## 4. Architecture to Implement

Each node is a link-state router for physical hazard:

```
Sensor read → dual-path conditioning (§5.2) → sensor fusion (§5.1) → 
  update own link-state entry if triggered → flood via ESP-NOW with seq_num (§5.4) → 
  neighbors accept only if seq_num is newer (§5.4) → 
  local Dijkstra over double-buffered link-state table (§5.3) → 
  shelter-in-place check (§6.2) → hold-down check (§5.5) → 
  LED color/animation decision (§6.1) → 
  gateway relays state to MQTT, best-effort, non-blocking, never on the decision path
```

Cluster ESP-NOW peers in groups of **≤15 nodes** (ESP-NOW's practical unencrypted peer ceiling is ~15–20) with a Zone Gateway node per cluster relaying condensed hazard summaries cross-cluster. Document this even if you only physically build one cluster for the MVP demo.

Synchronization between the ESP-NOW receive callback (WiFi/Core 1 context) and the routing task (pin to Core 0) must use a **double-buffered pointer swap**, not a mutex: the callback writes into the inactive buffer, then atomically swaps `active_ptr` once the write completes. The routing task only ever reads through `active_ptr`. This avoids priority inversion and torn reads without any lock on the hot path.

---

## 5. Exact Technical Specifications — implement these precisely

### 5.1 Cost formula
```
T_norm = clamp((T_current - T_baseline) / (T_critical - T_baseline), 0, 1)
S_norm = clamp((Smoke_ppm - S_baseline) / (S_critical - S_baseline), 0, 1)
O_norm = clamp(occupant_count / occupant_capacity, 0, 1)

hazard_multiplier = exp(alpha * T_norm + beta * S_norm)
congestion_term    = gamma * O_norm * base_distance     // additive, NEVER multiplied into hazard_multiplier

edge_cost = (base_distance * hazard_multiplier + congestion_term)
            * (FLAME_DETECTED ? BLOCK_MULTIPLIER : 1)
```
Congestion must be additive and decoupled from the hazard exponential — a multiplicative coupling would punish crowded exits *harder* exactly when hazard is worst, which is backwards (you want people moving, not redistributing for comfort, during severe hazard).

**Starting constants** (placeholders — refine via §5.7, but ship with these if the regression doesn't finish in time): `alpha = 2.2`, `beta = 1.6`, `gamma = 0.5`, `BLOCK_MULTIPLIER = 1×10⁶`.

### 5.2 Dual-path hazard detection
Run two independent conditioning paths per sensor stream:
- **Slow path:** EWMA smoothing for noise rejection, feeding an absolute-value delta threshold gate.
- **Fast path:** independent rate-of-change trigger, uncoupled from the EWMA, to catch a genuine flashover the slow filter would otherwise delay. **Require the rate threshold to be exceeded on 2 consecutive samples, not 1**, to filter single-sample ADC glitches while keeping almost all of the speed advantage.

A node updates its own link-state entry and floods an update if **either** path fires.

### 5.3 Link-state table
Double-buffered (see §4). Layout is identical in both buffers. Every node maintains the *entire* building's current table, not just its immediate neighbors'.

### 5.4 Mesh packet & sequencing
```c
struct HazardPacket {
  uint16_t node_id;
  uint32_t seq_num;         // monotonic per-node counter, wraparound handled via modular comparison
  uint32_t node_uptime_ms;  // this node's own clock only — never compared across nodes
  float    temp_c;
  float    smoke_ppm;
  bool     flame_detected;
  float    edge_cost;       // pre-fused — neighbors don't need raw sensor values
  uint16_t crc16;
};
```
- Accept an update from neighbor X only if `seq_num > last_seen_seq[X]` (mod-arithmetic, wraparound-safe) **and** CRC16 passes.
- Every node re-floods its own current packet every `REFRESH_INTERVAL_MS ≈ 2000ms` regardless of whether the value changed, incrementing `seq_num` each time. This is what bounds staleness given ESP-NOW has no delivery guarantee. **This periodic refresh is a separate mechanism from the event-triggered flood in §5.2** — event triggers bypass the 2s timer entirely and fire immediately, which is what keeps you inside the 300ms budget. Make sure your implementation and your documentation both make this distinction explicit; it's a natural point of confusion.
- **Staleness aging:** if no accepted packet arrives from neighbor X within `STALE_TIMEOUT_MS ≈ 6000ms` (≈3× refresh interval), X's edge cost decays upward on a defined curve toward "treat as fully hazardous" — it is **not** held at its last value and **not** snapped to a flat default. Critically: **a node's own edges are never affected by any neighbor's staleness** — see §6.3 for what *does* affect a node's own edges.

### 5.5 Hold-down / hysteresis
```
if new_next_hop != current_next_hop:
    if flame_detected on current_next_hop's edge:
        switch immediately                      // safety always overrides stability
    elif (time_since_last_switch < HOLD_DOWN_MS) and (new_cost > 0.7 * current_cost):
        keep current_next_hop                    // not meaningfully better yet — avoid flicker
    else:
        switch, reset last_switch_time
```
`HOLD_DOWN_MS ≈ 1500–2000ms`. At cold boot / first-ever computation, this must fall through to immediate switch (no artificial delay before a node's very first path assignment) — handle this as an explicit initialization case, don't rely on an uninitialized timer accidentally doing the right thing.

**Note for your own documentation:** the `0.7 ×` comparator here and the `STALE_TIMEOUT_MS` in §5.4 are control-flow thresholds governing *when* to re-evaluate or re-switch — not the cost function itself, which stays fully continuous per §5.1. Keep this distinction ready to explain; it can superficially look like the exact binary-threshold pattern §2.3 prohibits, but it isn't the same thing.

### 5.6 Timing budget — target and how to prove it
| Stage | Typical | p95 | Worst-case (1 retry) |
|---|---|---|---|
| Sensor read + dual-path conditioning + fusion | 1–5ms | 6ms | 8ms |
| Threshold / rate-spike check | <1ms | 1ms | 1ms |
| Local Dijkstra recompute (double-buffered) | 5–15ms | 18ms | 25ms |
| ESP-NOW propagation, per hop | 2–10ms | 15ms | 35ms |
| LED strip update (`FastLED.show()`) | 2–5ms | 6ms | 8ms |

Derive the multi-hop total explicitly rather than asserting it:
```
T_total = T_sense+fuse(once, origin) + T_threshold(once)
        + (hops × T_propagation_per_hop) + T_dijkstra(once, receiving node) + T_led(once)
```
For a 4-hop worst-affected node: p95 = 6+1+(4×15)+18+6 = **91ms**; worst-case = 8+1+(4×35)+25+8 = **182ms**. Both comfortably under 300ms with margin. **Measure this for real** — log on-device timestamps across ≥100 trigger bursts per hop-count, both on a clear bench and with an artificial WiFi-congestion generator running, and report actual measured numbers alongside this projected table, not instead of it.

### 5.7 Offline fusion-constant regression (one-time, not on-device)
Pull a public smoke/temperature time-series dataset (e.g. a Kaggle smoke-detection dataset, or NIST fire dynamics data). Fit a logistic-growth curve for slow smolder and a near-step function for flashover to give the injector's fire profiles realistic time constants, and refit `alpha`/`beta`/`gamma` from real data. Keep the fitting script under `simulator/fire_profiles/` and a one-paragraph summary of the result — this becomes both your injector's realism and a legitimate references-slide entry. If it doesn't finish in time, ship with §5.1's placeholder constants and say so explicitly rather than presenting them as final.

---

## 6. Mandatory Correctness Fixes (from adversarial review — do not treat any of these as optional)

### 6.1 LED color decision function
Fusing everything into one scalar `edge_cost` is correct for Dijkstra, but color needs its own logic to satisfy the literal "Yellow for high-smoke alternate route" requirement:
```c
LedState choose_led_state(EdgeDecision d) {
  if (d.next_hop_edge.flame_detected || d.current_edge.flame_detected)
    return RED_PULSE;                                  // immediate danger, always wins
  if (d.best_cost_to_exit >= SHELTER_THRESHOLD)
    return WHITE_STROBE;                                // see 6.2
  if (d.rerouted_from_original_shortest_path) {
    return (d.deciding_edge.S_norm > d.deciding_edge.T_norm)
      ? YELLOW        // smoke-dominant reroute
      : RED_PULSE;    // heat-dominant reroute — treat as danger, not advisory
  }
  return GREEN;
}
```
Chase-animation direction: scroll the strip's lit pattern from the "away from hazard" end toward the chosen next-hop end at a fixed offset-increment per animation tick. "Reversing direction" is just the sign of that increment flipping when next-hop changes physical side — implement it that simply, don't build a separate subsystem for it. Pulse rate/brightness scales with the deciding edge's hazard severity, independent of the color choice above.

### 6.2 Shelter-in-place state
When every path to every exit requires crossing at least one flame-blocked edge, enter a distinct state rather than silently returning the "least-bad" astronomically expensive path:
```c
float best_cost = dijkstra_result.cost_to_nearest_exit;
if (best_cost >= SHELTER_THRESHOLD)      // SHELTER_THRESHOLD = 100000
    enter_state(STATE_SHELTER_IN_PLACE);
else
    exit_state(STATE_SHELTER_IN_PLACE);  // auto-clears the instant a path reopens
```
`SHELTER_THRESHOLD = 100,000` is derived, not arbitrary: worst plausible single non-flame edge ≈ `base_distance(50m) × exp(alpha+beta)(≈44.7) ≈ 2,260`; worst plausible full 20-hop non-flame path ≈ `45,000`. `100,000` sits ~2× above that and 10× below `BLOCK_MULTIPLIER (1e6)` — comfortable margin on both sides. **Use `double` (or fixed-point) for this accumulator inside the MCU**, even though the wire packet keeps `edge_cost` as `float32` for bandwidth — a 32-bit float has too little precision once sums approach `1e6` while still needing to correctly compare smaller non-flame contributions.

Signal it distinctly: LED solid white slow-strobe, buzzer continuous tone (not the pulsed reroute alarm), dashboard tile reads "SHELTER-IN-PLACE — NO SAFE EGRESS" instead of a path arrow.

### 6.3 Three-tier sensor fail-safe hierarchy (closes the gap in naive "local-first" designs)
A design where a node's own sensor reading always wins over neighbor data is *necessary* (a node must never let a stale neighbor override good local data about itself) but **not sufficient** — it has no defense if the local sensor itself is the thing that's broken (stuck reading, disconnected wire, NaN from a driver, floating ADC pin). Implement a plausibility check and a three-tier fallback:

```c
struct SensorHealth {
  float   ring_buffer[10];
  uint8_t idx;
  bool    healthy;
};

void update_sensor_health(SensorHealth *h, float sample, float phys_min, float phys_max) {
  if (isnan(sample) || sample < phys_min || sample > phys_max) {
    h->healthy = false;                 // out-of-range or read error
    return;
  }
  h->ring_buffer[h->idx++ % 10] = sample;
  float variance = compute_variance(h->ring_buffer, 10);
  if (variance < SENSOR_NOISE_FLOOR && ring_buffer_spans_30s(h)) {
    h->healthy = false;                 // flat for 30s+ despite always having some
    return;                             // real-world noise → treat as stuck
  }
  h->healthy = true;
}
```
```
// Per outgoing edge of THIS node:
if (local_sensor_health.healthy):
    edge_hazard_input = this_node.local_reading          // Tier 1 — highest priority, unchanged principle
elif (has_reachable_neighbors_with_recent_data):
    edge_hazard_input = neighbor_consensus_estimate()     // Tier 2 — NEW: only invoked when local is proven bad
    dashboard_status = "SENSOR FAULT – using neighbor consensus"
else:
    edge_hazard_input = pre_flashed_static_default        // Tier 3 — same last resort as before
    dashboard_status = "SENSOR FAULT – isolated, static default"
```
The inversion (trusting neighbors over local) only activates when the local sensor is *provably* implausible — this doesn't weaken the original neighbor-staleness protection, it adds the missing mirror-image case. Surface `dashboard_status` on the Node Health Panel. Build a live demo for this exact scenario (disconnect a sensor lead on one node, show the dashboard flag it and routing correctly defer to consensus) as a third fail-safe beat alongside the existing corrupt-packet and kill-a-node demos — this gives you a provable answer for all three of the rubric's named fail-safe scenarios (drop, corruption, sensor failure), not two out of three.

### 6.4 Schema additions
```
EDGES {
    ...
    occupant_capacity  INT   // corridor/doorway capacity — denominator for O_norm in §5.1,
}                             // hand-authored per edge in the graph JSON, same pattern as base_distance

NODES {
    ...
    T_baseline, T_critical, S_baseline, S_critical   FLOAT   // per-node calibration, not global constants
}
```
Occupancy is sensed at **node** granularity (matches how access-control/camera systems are physically mounted — at doorways/junctions), then applied to that node's outgoing edges when computing each edge's `O_norm`. Document this explicitly in the graph JSON schema, not just implicitly in code.

### 6.5 Floor-transition edges
Edges where `node_a.floor != node_b.floor` (stairwells) carry `floor_transition = true` and a `base_distance` reflecting real traversal time (15–20s-equivalent vs. a same-floor corridor edge). Dijkstra treats them as ordinary edges — no algorithm change needed, only graph data. Validate against a synthetic 2-floor test graph even if the physical MVP only wires up one floor.

---

## 7. Repository Structure to Produce

```
fire-evac-router/
├── firmware/                 # ESP32 C/C++ (PlatformIO)
│   ├── src/                  # main.cpp, routing.cpp, fusion.cpp, comms.cpp, leds.cpp, failsafe.cpp
│   ├── include/               # HazardPacket, seq_num logic, shared headers
│   ├── lib/                   # FastLED, ESP-NOW wrapper
│   └── platformio.ini
├── simulator/                 # Python digital twin / injector
│   ├── graph_model.py          # topology + per-node calibration loader
│   ├── fire_profiles/           # slow-smolder.py, flashover.py, regression script (§5.7)
│   ├── injector.py              # serial + MQTT injection, CLI/API control, corrupt-packet mode
│   └── requirements.txt
├── dashboard/                  # Node-RED flow + custom UI
│   ├── flows.json
│   └── ui/                     # 2D floor grid, shelter-in-place indicator, node health panel
├── docs/                       # architecture diagrams, engineering report
├── tests/
│   ├── firmware/                 # fusion, routing, seq_num acceptance, hold-down, sensor-health, shelter-in-place
│   ├── simulator/                  # profile-curve tests, corrupt-packet generator tests
│   └── integration/                 # end-to-end scenario scripts
├── docker/
│   ├── mosquitto/
│   └── docker-compose.yml            # broker + Node-RED
├── scripts/                    # build/flash-all, demo-rehearsal runner
└── README.md
```

---

## 8. Build Order — execute in this sequence; each task lists its Definition of Done

1. **Scaffold + protocol contracts.** Create the folder structure above. Define `HazardPacket` (§5.4) and the building-graph JSON schema (§6.4, incl. per-node calibration and `floor_transition`). **DoD:** schema compiles/parses; struct matches §5.4 byte-for-byte.
2. **Single-node firmware core.** Hardcode a small graph on one node; implement Dijkstra; split routing vs. LED animation across FreeRTOS tasks pinned to separate cores, synchronized via the double-buffer pattern (§4), not a mutex. **DoD:** one node computes and displays a correct path for a manually-set hazard value, non-blocking (no `delay()` in the hot path).
3. **Sensor fusion + mesh.** Implement §5.1's decoupled cost formula, §5.2's dual-path detection (with the 2-sample debounce), ESP-NOW send/recv with §5.4's sequence-numbered flood and staleness aging, and §5.5's hold-down logic. **DoD:** 3+ nodes reroute consistently and without visible LED flicker when one node's hazard changes; a replayed old packet is correctly rejected.
4. **Injector + fail-safe.** Build the Python injector with ≥2 fire-growth profiles, judge-triggerable manual zone selection, and a corrupt-packet mode. Implement CRC16 validation, §6.3's three-tier sensor fail-safe, and §6.2's shelter-in-place state. **DoD:** live demo proves (a) corrupt packets are rejected and logged, (b) a killed node doesn't stop the mesh, (c) a locally-failed sensor correctly defers to neighbor consensus and flags itself, (d) an all-paths-blocked scenario correctly enters and auto-clears shelter-in-place.
5. **Gateway + dashboard.** MQTT bridge (non-blocking, best-effort, read-only path), Node-RED 2D floor grid, node health panel, shelter-in-place indicator. **DoD:** dashboard reflects live mesh state including the new sensor-fault status from §6.3; killing the dashboard/WiFi does not affect mesh routing correctness.
6. **Integration + worst-case timing.** Wire real hardware (or finalize a Wokwi simulation running the actual firmware binary). Run the timing methodology from §5.6 — ≥100 trigger bursts per hop-count, both clear-bench and under artificial WiFi congestion — and report real measured p95/worst-case numbers next to the projected table. **DoD:** measured worst-case is under 300ms with margin; if not, document the gap and the specific stage responsible.
7. **Docs + presentation.** Engineering report with the sensor-threshold → edge-weight flowchart (§3.6), architecture diagrams, and a dedicated section on the §6.3 fail-safe design. Presentation covering: system overview, technical approach, feasibility/viability (explicitly separate hazard-node hardware cost from occupancy-sensing infrastructure cost; frame the system as augmenting — not replacing — code-mandated static signage), artifacts/screenshots, references (including the §5.7 dataset). **DoD:** report and slides exist as final files; every claim in the slides has a corresponding demoable artifact.

---

## 9. Deliverables Checklist

- [ ] Firmware source (C/C++, PlatformIO, non-blocking, double-buffered, commented)
- [ ] Python injector (≥2 fire profiles, live zone trigger, corrupt-packet trigger)
- [ ] Node-RED dashboard export + screenshots, including shelter-in-place and sensor-fault views
- [ ] Engineering report with the required flowchart
- [ ] Presentation deck
- [ ] README with setup/flash/run instructions
- [ ] Test suite covering: fusion correctness, Dijkstra correctness, seq_num acceptance/rejection, hold-down/no-flicker, sensor-health tiering, shelter-in-place trigger and auto-clear
- [ ] Measured (not just projected) worst-case timing data
- [ ] All three fail-safe scenarios (drop, corruption, sensor failure) independently demoable

---

## 10. Guardrails — do not do these things

- Do not put any ML/DL/LLM inference on the MCU's decision path (§1).
- Do not make routing depend on the dashboard, MQTT broker, or gateway being reachable.
- Do not implement the cost function as a step/threshold function for temperature or smoke — flame's Boolean gate is the one legitimate exception (§2.3).
- Do not use a mutex for the link-state table sync — use the double-buffer swap (§4).
- Do not let a node's own local sensor reading be trusted unconditionally without the plausibility check in §6.3 — this was the single most serious defect found in earlier review of this design and must not silently reappear.
- Do not treat any item in §6 as a stretch goal — they are correctness fixes, not enhancements.