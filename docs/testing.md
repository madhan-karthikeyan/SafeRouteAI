# SafeRouteAI — Testing Guide

## Test Structure

```
tests/
  backend/
    test_engine.py      Dijkstra, cost formula, shelter threshold, edge cases
    test_api.py         REST endpoints, inject, reset, replay
  firmware/
    test_dijkstra.py    Python reference validation of routing algorithm
    test_fusion.py      Sensor fusion cost formula + dual-path filtering
    test_holddown.py    Hysteresis behavior of hold-down switching
    test_sensor_health.py  NaN rejection, range validation, stuck detection
    test_seqnum.py      Anti-replay sequence number acceptance logic
  simulator/
    test_profiles.py    Fire growth curve profiles (slow smolder, flashover)
  integration/
    test_scenarios.py   End-to-end: corrupt packets, shelter trigger, profiles

test/
  firmware/
    test_dijkstra.cpp   Unity C++ on-device unit test (PlatformIO)
```

---

## Running Tests

### All Tests

```bash
./scripts/run-all-tests.sh
```

This runs firmware Python reference tests, simulator tests, and integration tests sequentially.

### Backend Tests

```bash
# Pytest
python -m pytest tests/backend/ -v

# Direct execution
python tests/backend/test_engine.py
python tests/backend/test_api.py
```

### Firmware Python Reference Tests

```bash
python tests/firmware/test_dijkstra.py
python tests/firmware/test_fusion.py
python tests/firmware/test_holddown.py
python tests/firmware/test_sensor_health.py
python tests/firmware/test_seqnum.py
```

### Firmware C++ On-Device Tests

```bash
pio test --environment esp32dev
```

This compiles and runs `test/firmware/test_dijkstra.cpp` using the Unity test framework on the ESP32.

### Simulator Tests

```bash
python tests/simulator/test_profiles.py
```

### Integration Tests

```bash
python tests/integration/test_scenarios.py
```

---

## Backend Tests

### `test_engine.py` — Simulation Engine (240 lines, 190+ assertions)

Validates the engine that powers both the mock frontend and the backend simulation.

| Test | What it verifies |
|---|---|
| `test_dijkstra_finds_exit` | Every non-exit node has a reachable exit path; path starts at source, ends at exit, has no loops |
| `test_dijkstra_shelter_threshold` | When all paths are blocked by flashover fire, `_dijkstra` returns `None` (shelter-in-place) |
| `test_route_changes_after_fire` | Placing fire on the original path forces a different route; blocked node cost ≥ `SHELTER_THRESHOLD` |
| `test_edge_cost_zero_self_loop` | Edge cost from a node to itself is 0.0 |
| `test_edge_cost_nonzero` | Adjacent node edge cost is > 0 |
| `test_edge_cost_symmetry` | Cost A→B equals cost B→A (within 0.001) |
| `test_compute_next_hop_returns_none_for_exit` | Exit nodes return `None` (no hop needed) |
| `test_compute_next_hop_non_exit` | Sensor nodes return a valid neighbor as next hop |
| `test_build_routes_returns_valid_routes` | Route list non-empty; each route has ≥2 nodes, valid priority 0-1 |
| `test_build_node_states_all_nodes` | Every graph node has state; temperature 20-500; smoke 0-1; occupants ≥ 0 |
| `test_occupants_distribution` | Total occupants > 0 |
| `test_snapshot_serializable` | Snapshot dumps to dict with correct types |
| `test_known_cost_value` | Computed cost ≥ base distance; cost < shelter threshold; cost formula matches firmware |
| `test_golden_cost_formula` | 8 golden (T_norm, S_norm, O_norm, distance, flame) → cost mappings cross-validated against firmware constants |
| `test_golden_flame_cost_dominates` | Fire on path multiplies cost by `BLOCK_MULTIPLIER`, exceeding shelter threshold |

### `test_api.py` — REST API (116 lines, 10+ assertions)

Uses FastAPI `TestClient` to validate HTTP endpoints.

| Test | What it verifies |
|---|---|
| `test_get_buildings` | `GET /api/buildings` returns 200 + list with id, name, type, floors |
| `test_get_graph` | `GET /api/graph` returns 200 with nodes, edges, floors, hazardGrid |
| `test_get_graph_with_building_id` | `?buildingId=mega-mall` returns matching building id |
| `test_inject_and_reset` | POST inject then reset both return 200 |
| `test_inject_invalid_scenario` | POST with unknown scenario still returns 200 |
| `test_health` | `GET /api/health` returns status=ok, buildings count, ws count |
| `test_replay` | `GET /api/replay` returns a list |

---

## Firmware Tests

### `test/firmware/test_dijkstra.cpp` — C++ On-Device

Unity-based unit test that compiles for ESP32. Validates the actual `routing_compute` function running on target hardware. Tests basic pathfinding and flame-blocked routing on a small graph.

### `tests/firmware/test_dijkstra.py` — Python Reference (85 lines)

Validates the Dijkstra algorithm independently of the C++ build:

| Test | What it verifies |
|---|---|
| `test_basic_path` | 3-node line graph; path cost 1→3 equals sum of edge costs; cost < shelter threshold |
| `test_flame_blocked` | Flame on edge 2→3 forces routing around it; distance to node 2 stays below shelter threshold |

### `tests/firmware/test_fusion.py` — Cost Formula (64 lines)

| Test | What it verifies |
|---|---|
| `test_no_hazard` | Zero hazard produces cost equal to base distance |
| `test_full_hazard_no_flame` | Full hazard cost > base but < shelter threshold |
| `test_flame_block` | Flame multiplies cost by `BLOCK_MULTIPLIER` |
| `test_shelter_threshold_crossed` | Extreme hazard + flame exceeds `SHELTER_THRESHOLD` |
| `test_continuous_no_step` | Cost strictly increases with T_norm (no step functions) |
| `test_congestion_additive_not_multiplicative` | Congestion term is additive (`GAMMA * O_norm * dist`), not multiplicative |

### `tests/firmware/test_holddown.py` — Hold-Down Hysteresis (68 lines)

| Test | What it verifies |
|---|---|
| `test_initial_switch` | First path is accepted immediately |
| `test_flame_overrides_hold` | Flame on current edge bypasses hold-down timer |
| `test_hold_suppresses_small_change` | Within hold-down window, high-cost switches are suppressed |
| `test_switch_after_hold_expires` | After hold-down period (1800ms), new routes are accepted |

The hold-down algorithm (`hold_down_should_switch`):
1. If new hop is 0, reject
2. If no current hop, accept (initial path)
3. If flame detected on current edge, accept immediately
4. If path not yet set, accept
5. If within `HOLD_DOWN_MS` (1800ms) AND new cost > 0.7 × SHELTER_THRESHOLD, suppress
6. Otherwise accept

### `tests/firmware/test_sensor_health.py` — Sensor Health (63 lines)

| Test | What it verifies |
|---|---|
| `test_nan_rejected` | NaN samples mark sensor unhealthy |
| `test_out_of_range_rejected` | Samples outside [phys_min, phys_max] mark sensor unhealthy |
| `test_valid_accepted` | Varying sine-wave samples within range keep sensor healthy |
| `test_stuck_detected` | Constant reading for 60s (variance < noise floor) marks sensor stuck |

The health algorithm:
1. NaN or out-of-range → immediately unhealthy
2. After 10 samples over 30s window → compute variance
3. Variance < `SENSOR_NOISE_FLOOR` → stuck sensor

### `tests/firmware/test_seqnum.py` — Sequence Number (46 lines)

| Test | What it verifies |
|---|---|
| `test_accept_new` | Strictly increasing sequence numbers are accepted |
| `test_reject_old` | Equal or lower sequence numbers are rejected |
| `test_accept_after_wraparound` | 32-bit wraparound (0xFFFFFFF0 → 0x00000005) is correctly handled |
| `test_accept_same_node` | Per-node sequence tracking is independent |

---

## Simulator Tests

### `tests/simulator/test_profiles.py` — Fire Profiles (70 lines)

| Test | What it verifies |
|---|---|
| `test_slow_smolder_initial` | Slow smolder starts at ~25°C, smoke near 0 |
| `test_slow_smolder_after_30s` | After 30s: temp > 30°C, smoke > 50 ppm |
| `test_slow_smolder_final` | After 120s: temp > 60°C |
| `test_flashover_initial` | Flashover starts at ~25°C |
| `test_flashover_after_5s` | After 5s: temp > 100°C, flame detected |
| `test_flashover_final` | After 20s: temp > 200°C, smoke > 2000 ppm |

---

## Integration Tests

### `tests/integration/test_scenarios.py` — End-to-End (89 lines)

| Test | What it verifies |
|---|---|
| `test_graph_model` | Default building graph has 6+ nodes, 8+ edges; round-trip serialization works |
| `test_fire_profiles` | Slow smolder rises over 60s; flashover spikes flame + temp within 10s |
| `test_corrupt_packet_rejected` | Valid packets pass CRC check; corrupt mode generates invalid CRC |
| `test_shelter_in_place_trigger` | Flashover on a node sets flame, temp > 100°C, edge_cost ≥ SHELTER_THRESHOLD (100000) |

---

## Testing Methodology

### Golden Cost Formula Cross-Validation

The same edge cost formula is implemented in four places. Tests ensure all four match:

```
cost = base_dist * exp(ALPHA * T_norm + BETA * S_norm) + GAMMA * O_norm * base_dist
if flame: cost *= BLOCK_MULTIPLIER
```

Constants shared everywhere: `ALPHA=2.2`, `BETA=1.6`, `GAMMA=0.5`, `BLOCK_MULTIPLIER=1e6`, `SHELTER_THRESHOLD=100000.0`.

| Implementation | Location |
|---|---|
| Firmware C++ | `firmware/src/routing.cpp` `compute_edge_cost()` |
| Backend Python | `backend/engine.py` `compute_edge_cost()` |
| MQTT Bridge | `backend/mqtt_bridge.py` `_compute_edge_cost()` |
| Frontend TypeScript | `frontend/src/simulation/engine.ts` |
| Python Reference | `tests/firmware/test_fusion.py` |
| Golden Test Vectors | `tests/backend/test_engine.py` `test_golden_cost_formula()` |

The `test_golden_cost_formula` function in `test_engine.py` contains 8 explicit test vectors that serve as the cross-implementation contract:

```python
(0.0, 0.0, 0.0, 10.0, False, 10.0),                          # no hazard
(0.5, 0.0, 0.0, 10.0, False, 10.0 * exp(2.2 * 0.5)),         # moderate temp
(1.0, 0.0, 0.0, 10.0, False, 10.0 * exp(2.2)),                # max temp
(0.0, 1.0, 0.0, 10.0, False, 10.0 * exp(1.6)),                # max smoke
(0.0, 0.0, 0.5, 10.0, False, 10.0 + 0.5*0.5*10.0),           # congestion
(0.0, 0.0, 0.0, 10.0, True, 10.0 * BLOCK_MULTIPLIER),         # flame blocked
(0.3, 0.2, 0.1, 15.0, False, complex),                        # mixed
(0.8, 0.7, 0.3, 5.0, True, complex * BLOCK_MULTIPLIER),       # mixed + flame
```

### Hold-Down Hysteresis Verification

The firmware's `HOLD_DOWN_MS = 1800ms` prevents route flapping. Python `test_holddown.py` mirrors the C `hold_down_should_switch` logic exactly and verifies: initial accept, flame override, suppression within window, and expiration.

### State Machine Transition Testing

System status transitions are computed by `compute_status()` in `backend/engine.py`:

```
NORMAL → FIRE_DETECTED (smoke > 0.4)
FIRE_DETECTED → EVACUATION_ACTIVE (flame detected)
EVACUATION_ACTIVE → SHELTER_IN_PLACE (flame > 0 AND isolated > 4)
EVACUATION_ACTIVE → NO_SAFE_EXIT (flame > 6)
```

### Edge Case Coverage

| Scenario | Test |
|---|---|
| Fire on every path | `test_dijkstra_shelter_threshold` → shelter-in-place |
| Self-loop edge | `test_edge_cost_zero_self_loop` → cost = 0 |
| Extreme high hazard | `test_golden_flame_cost_dominates` → cost ≥ SHELTER_THRESHOLD |
| NaN sensor reading | `test_nan_rejected` → sensor marked unhealthy |
| Stuck sensor reading | `test_stuck_detected` → variance check catches it |
| Sequence wraparound | `test_accept_after_wraparound` → 32-bit overflow handled |
| Corrupt CRC packet | `test_corrupt_packet_rejected` → CRC16 mismatch detected |
| Symmetric cost | `test_edge_cost_symmetry` → A→B = B→A |

---

## How to Add New Tests

1. **Identify the layer**: backend, firmware (Python ref or C++ on-device), simulator, or integration
2. **Place the test file**: in the corresponding directory under `tests/`
3. **Follow the pattern**:
   - Backend tests: use `pytest` or standalone `check()` assertions
   - Firmware Python tests: standalone scripts with `test_*` functions
   - Firmware C++ tests: Unity framework in `test/firmware/`
   - Simulator tests: standalone `test_*.py` scripts
   - Integration tests: `test_scenarios.py` uses the Injector API
4. **Add golden vectors** if testing the cost formula
5. **Verify** with the appropriate command (see "Running Tests" above)

For on-device firmware tests (`test/firmware/test_dijkstra.cpp`), add your test to the existing Unity file and run with `pio test --environment esp32dev`.

---

## Simulation Test Scenarios

The integration tests (`tests/integration/test_scenarios.py`) use the Injector to simulate real-world conditions:

### Corrupt Packet Rejection

```
injector.set_corrupt_mode(True)
packet = injector.packet_for_node(node_id)
assert not packet_crc_valid(packet)  # CRC16 fails validation
```

This matches the firmware's `hazard_packet_validate()` function which computes CRC16 over the packet header and compares against the stored CRC.

### Shelter-in-Place Trigger

```
injector.trigger_flashover(node_id)
readings = injector.get_readings(node_id, now=future_time)
assert readings["flame_detected"] == True
assert readings["temp_c"] > 100
assert readings["edge_cost"] >= SHELTER_THRESHOLD  # 100000
```

When edge cost reaches `SHELTER_THRESHOLD`, the firmware's `routing_compute` returns `shelter_in_place=true`, triggering the white strobe LED and halting evacuation.

### Fire Profile Execution

Slow smolder profile ramps temperature gradually over 2 minutes, while flashover spikes to 200°C+ within 20 seconds. Both follow realistic t-squared fire growth curves.
