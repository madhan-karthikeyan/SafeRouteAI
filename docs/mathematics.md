# SafeRouteAI — Mathematical Foundations

## 1. Edge Cost Formula

The core of SafeRouteAI's routing is a **continuous, exponential edge cost function** that combines temperature, smoke, occupancy, and flame presence into a single scalar traversal cost.

### Complete Formula

```latex
T_norm = clamp((T_current - T_baseline) / (T_critical - T_baseline), 0, 1)

S_norm = clamp((Smoke_ppm - S_baseline) / (S_critical - S_baseline), 0, 1)

O_norm = clamp(occupant_count / occupant_capacity, 0, 1)

hazard_multiplier = exp(2.2 * T_norm + 1.6 * S_norm)

congestion_term = 0.5 * O_norm * base_distance

edge_cost = (base_distance * hazard_multiplier + congestion_term) * (FLAME_DETECTED ? 1e6 : 1)
```

### C Implementation

```c
float compute_edge_cost(float T_norm, float S_norm, float O_norm,
                         float base_dist, bool flame, float cap) {
    float hazard_mult = expf(2.2f * T_norm + 1.6f * S_norm);
    float congestion_term = 0.5f * O_norm * base_dist;
    float cost = base_dist * hazard_mult + congestion_term;
    if (flame) {
        cost *= 1000000.0f;  // BLOCK_MULTIPLIER
    }
    return cost;
}
```

### Constants

| Symbol | Value | Description |
|--------|-------|-------------|
| α | 2.2 | Temperature hazard exponent weight |
| β | 1.6 | Smoke hazard exponent weight |
| γ | 0.5 | Congestion coefficient |
| `BLOCK_MULTIPLIER` | 1,000,000 | Flame presence cost multiplier |
| `SHELTER_THRESHOLD` | 100,000 | Cost above which shelter-in-place is ordered |
| `T_baseline` | 25.0 °C | Normal operating temperature |
| `T_critical` | 80.0 °C | Temperature at which hazard saturates |
| `S_baseline` | 0.0 ppm | Normal smoke level |
| `S_critical` | 1000.0 ppm | Smoke level at which hazard saturates |

---

## 2. Normalization Rationale

Each sensor modality is **independently normalized to [0, 1]** before combination. This is a deliberate design choice with three benefits:

### Why Per-Sensor Normalization?

**1. Heterogeneous units → homogeneous scale**

Temperature (°C) and smoke (ppm) have different units and ranges. Direct multiplication without normalization would let the sensor with the larger numeric range dominate the cost.

```
Before normalization:
  temp = 80°C, smoke = 1000 ppm
  → 80 * 1000 = 80,000 (smoke dominates purely by magnitude)

After normalization:
  T_norm = 1.0, S_norm = 1.0
  → exp(2.2*1.0 + 1.6*1.0) = exp(3.8) ≈ 44.7 (balanced contribution)
```

**2. Sensor-agnostic thresholds**

Each node has its own `T_baseline`, `T_critical`, `S_baseline`, and `S_critical` values stored in the building graph. This allows different areas (e.g., kitchen vs. hallway) to have different hazard sensitivity without changing the routing algorithm.

**3. Clamping prevents edge-case blowup**

The `clamp(..., 0, 1)` ensures that a sensor reading outside its calibrated range (e.g., temperature sensor short-circuit reading 65535°C) does not produce infinite or NaN costs.

```c
float clampf(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
```

---

## 3. Exponential Weighting Justification

### Why Exponential?

Traditional fire alarm systems use **binary thresholds** (e.g., "temperature > 60°C → alarm"). This creates:

- **Threshold flicker:** A sensor reading oscillating around 60°C causes repeated alarm/clear cycles
- **Loss of gradient information:** 59°C and 20°C produce the same cost (zero), discarding useful information
- **No anticipatory routing:** Routes cannot begin diverting until a hard threshold is crossed

SafeRouteAI uses a **continuous exponential function**:

```latex
hazard_multiplier = exp(2.2 * T_norm + 1.6 * S_norm)
```

### Properties

| Property | Behavior |
|----------|----------|
| T_norm = 0, S_norm = 0 | `exp(0) = 1` → base distance only |
| T_norm = 0.5, S_norm = 0 | `exp(1.1) ≈ 3.0` → 3× effective distance |
| T_norm = 1, S_norm = 1 | `exp(3.8) ≈ 44.7` → 45× effective distance |
| Flame detected | ×1,000,000 additional multiplier |
| Strict monotonicity | Higher hazard always → higher cost (no flat zones) |
| Continuous | No step discontinuities (no threshold flicker) |

### Strict Monotonicity Test

```python
def test_continuous_no_step():
    for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
        c1 = compute_edge_cost(t, 0, 0, 10, False)
        c2 = compute_edge_cost(t + 0.01, 0, 0, 10, False)
        assert c2 > c1, "Cost must be strictly increasing"
```

---

## 4. Dijkstra Algorithm

Each ESP32 node runs **Dijkstra's shortest-path algorithm** on its local copy of the building graph, using the dynamic edge costs computed from the link state table.

### Algorithm Description

```latex
Input:  Graph G = (V, E), source node s
        Edge weight function w(u, v) = compute_edge_cost(...)
Output: dist[v] = shortest path cost from s to v
        prev[v] = previous node on shortest path

Algorithm:
    for each v in V:
        dist[v] = INFINITY
        prev[v] = null
    dist[s] = 0
    unvisited = V

    while unvisited is not empty:
        u = argmin_{v in unvisited} dist[v]   // linear scan (O(V))
        unvisited.remove(u)

        if dist[u] == INFINITY: break

        for each neighbor v of u:
            w = edge_cost(u, v)
            alt = dist[u] + w
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u

    // Find nearest exit
    nearest_exit = argmin_{v where is_exit[v]} dist[v]
```

### Complexity

| Implementation | Complexity |
|----------------|------------|
| Current firmware (linear scan) | O(V² + E) |
| With priority queue (binary heap) | O((V + E) log V) |

The firmware uses a **linear scan** to find the minimum-distance unvisited node (`O(V)`) because `MAX_NODES = 15` makes the constant overhead of a heap not worthwhile.

### Exit Selection

```c
// After Dijkstra completes
int nearest_exit = -1;
double best_cost = INFINITY;
for (int i = 0; i < graph->node_count; i++) {
    if (is_exit[i] && dist[i] < best_cost) {
        best_cost = dist[i];
        nearest_exit = i;
    }
}

// Shelter-in-place if all exits are too costly
if (best_cost >= SHELTER_THRESHOLD) {
    result.shelter_in_place = true;
    return;
}

// Walk predecessor chain to find first hop
result.next_hop = walk_predecessors(prev, nearest_exit);
```

---

## 5. Sensor Fusion Math

SafeRouteAI uses a **dual-path fusion filter** that combines a slow EWMA (Exponentially Weighted Moving Average) with a fast rate-of-change detector.

### Dual-Path Architecture

```latex
                ┌──────────────────────┐
raw_sample ────→│  EWMA Slow Path      │──→ filtered_value
                │  α = 0.3             │
                └──────────────────────┘
                ┌──────────────────────┐
raw_sample ────→│  Rate-of-Change      │──→ trigger (2-sample debounce)
                │  Fast Path           │
                └──────────────────────┘
```

### EWMA Filter (Slow Path)

```latex
EWMA_new = α * raw_sample + (1 - α) * EWMA_old
```

Where `α = 0.3` (configurable per filter instance).

| α | Effect |
|---|--------|
| 0.0 | No update (infinite hold) |
| 0.3 | Moderate smoothing (~3 samples to 70% of step) |
| 0.5 | Light smoothing |
| 1.0 | No filtering (raw passthrough) |

### C Implementation

```c
f->ewma = f->alpha * raw_sample + (1.0f - f->alpha) * f->ewma;
```

### Rate-of-Change Detection (Fast Path)

Two mechanisms trigger on rapid changes:

**1. EWMA Delta Detection**

```latex
delta = |EWMA_new - EWMA_old|
trigger if delta >= delta_threshold
```

Where `delta_threshold = 2.0°C` (temperature) or `10.0 ppm` (smoke).

**2. Raw Rate Detection with 2-Sample Debounce**

```latex
rate = raw_sample - prev_raw_sample

if |rate| >= rate_threshold:
    rate_trigger_count++
    if rate_trigger_count >= 2:
        trigger = true
        rate_trigger_count = 0
else:
    rate_trigger_count = 0
```

The **2-sample debounce** (consecutive samples both exceeding threshold) prevents single-sample noise spikes from triggering route recomputation.

```c
bool dual_path_update(DualPathFilter *f, float raw_sample) {
    // Slow path: EWMA update
    float old_ewma = f->ewma;
    f->ewma = f->alpha * raw_sample + (1.0f - f->alpha) * f->ewma;

    // Fast path: delta detection
    float delta = fabsf(f->ewma - old_ewma);
    if (delta >= f->delta_threshold) triggered = true;

    // Fast path: rate detection with 2-sample debounce
    float rate = raw_sample - f->prev_raw;
    if (fabsf(rate) >= f->rate_threshold) {
        f->rate_trigger_count++;
        if (f->rate_trigger_count >= 2) {
            triggered = true;
            f->rate_trigger_count = 0;
        }
    } else {
        f->rate_trigger_count = 0;
    }

    return triggered;
}
```

### Filter Parameters

| Filter | α | delta_threshold | rate_threshold |
|--------|---|-----------------|----------------|
| Temperature | 0.3 | 2.0 °C | 5.0 °C/sample |
| Smoke | 0.3 | 10.0 ppm | 50.0 ppm/sample |

---

## 6. Occupancy Cost Modeling

Occupancy is modeled as an **additive congestion term** on the edge cost, not a multiplier. This ensures that congestion adds a fixed overhead regardless of the underlying hazard level.

```latex
congestion_term = 0.5 * O_norm * base_distance

edge_cost = base_distance * hazard_multiplier + congestion_term
```

### Rationale

- **Additive, not multiplicative:** Congestion should not amplify the hazard multiplier. A smoky but empty corridor and a smoky packed corridor should differ by a fixed overhead, not a factor.
- **Normalized occupancy:** `O_norm = clamp(occupant_count / occupant_capacity, 0, 1)` ensures the term is bounded.
- **Distance-proportional:** Longer corridors have more congestion capacity, so the term scales with `base_distance`.

### Test Verification

```python
def test_congestion_additive_not_multiplicative():
    no_cong = compute_edge_cost(0.5, 0.5, 0, 10, False)
    with_cong = compute_edge_cost(0.5, 0.5, 1.0, 10, False)
    diff = with_cong - no_cong
    assert abs(diff - GAMMA * 1.0 * 10) < 0.01  # γ * O_norm * base_dist
```

---

## 7. Threshold Logic

### Flame Cost Dominance

When a flame is detected on a node, the edge cost receives a **1,000,000× multiplier**, effectively blocking traversal through that edge.

```latex
FLAME_DETECTED ? edge_cost *= 1,000,000 : edge_cost
```

This ensures that:
- Any path through a flame node has cost ≥ 10,000,000 (assuming 10m base distance)
- Dijkstra will always find an alternate route if one exists
- Only when ALL routes are blocked does shelter-in-place activate

### Shelter-in-Place Threshold

When the lowest-cost path to any exit exceeds **100,000**, the node enters shelter-in-place mode:

```c
#define SHELTER_THRESHOLD 100000.0

if (best_cost >= SHELTER_THRESHOLD) {
    result.shelter_in_place = true;
    result.next_hop = 0;
    return;
}
```

This threshold is crossed when:
- Base distance × hazard_multiplier > 100,000 (e.g., 2km route at maximum hazard)
- Any flame is on the only egress path (cost ≥ 10,000,000)
- Multiple edges are blocked, forcing extremely long detours

### LED State Determination

```c
LedColor choose_led_state(const EdgeDecision *d, DijkstraResult *res) {
    if (res->shelter_in_place)   return LED_WHITE_STROBE;
    if (d->flame_detected_on_current || d->flame_detected_on_next)
                                 return LED_RED_PULSE;
    if (res->cost_to_exit >= SHELTER_THRESHOLD)
                                 return LED_WHITE_STROBE;
    if (d->rerouted_from_original) {
        return (d->deciding_edge_S_norm > d->deciding_edge_T_norm)
               ? LED_YELLOW : LED_RED_PULSE;
    }
    return LED_GREEN;
}
```

| LED Color | Meaning | Condition |
|-----------|---------|-----------|
| Green | Safe | `cost_to_exit < SHELTER_THRESHOLD`, no reroute, no flame |
| Yellow | Caution (smoke-driven reroute) | Rerouted, smoke > temperature contribution |
| Red Pulse | Fire nearby | Flame on current edge or next hop |
| White Strobe | Shelter in place | No safe egress path exists |

---

## 8. EWMA Filter Equation

The Exponentially Weighted Moving Average is the core smoothing mechanism for raw sensor readings.

### Definition

```latex
y_0 = x_0
y_t = α * x_t + (1 - α) * y_{t-1}
```

Where:
- `y_t` = filtered output at time t
- `x_t` = raw sensor reading at time t
- `α` = smoothing factor (0 < α ≤ 1)

### Step Response

The EWMA reaches `(1 - 1/e)` ≈ 63.2% of a step change after `1/α` samples:

```latex
n_63 = 1/α = 1/0.3 ≈ 3.3 samples
```

At a 50ms loop interval, this means the filter reaches ~63% of a step in ~167ms.

### Frequency Response

```latex
y_t / x_t = α / (1 - (1 - α) * z^{-1})
```

The filter has a single pole at `z = 1 - α`, acting as a low-pass with cutoff:

```latex
f_c = (α / (2 * π * Δt)) Hz
```

With `α = 0.3` and `Δt = 0.05s`:

```latex
f_c ≈ 0.3 / (2 * π * 0.05) ≈ 0.95 Hz
```

All frequency content above ~1 Hz is attenuated.

---

## 9. Rate-of-Change Detection Formula

The rate-of-change detector identifies rapid environmental changes that the slow EWMA would miss.

### Raw Rate

```latex
rate_t = x_t - x_{t-1}
```

### Threshold Test

```latex
trigger_count_{t} = trigger_count_{t-1} + 1,  if |rate_t| ≥ rate_threshold
                    0,                          otherwise

trigger = (trigger_count_t ≥ 2)
```

### Combined Trigger

```latex
triggered = (|y_t - y_{t-1}| ≥ delta_threshold) OR (trigger_count_t ≥ 2)
```

The dual-path design ensures:

| Scenario | EWMA Path | Rate Path | Result |
|----------|-----------|-----------|--------|
| Slow temperature rise (0.1°C/s) | Catches it after ~3s | Below threshold | Route update at next periodic broadcast |
| Sudden flame ignition (+200°C in 1s) | Takes ~3 samples to respond | **Catches immediately** | Immediate broadcast |
| Single-sample noise spike | Filtered out | Debounce prevents false trigger | No route change |
| Gradual smoke buildup | Smooth tracking | No trigger | Periodic updates only |

---

## 10. IDW Heatmap Interpolation

The backend transforms per-node hazard values into a continuous 2D heatmap grid using **Inverse Distance Weighting (IDW)**.

### Formula

```latex
h(g) = Σ_i w_i * h_i / Σ_i w_i

where:
  w_i = 1 / d(g, p_i)²   (inverse squared distance)
  d(g, p_i) = Euclidean distance from grid cell g to node i
  h_i = hazard value at node i
```

### Python Implementation

```python
def interpolate_heatmap(graph, nodes, floor):
    grid = [0.0] * (GRID_COLS * GRID_ROWS)

    floor_nodes = [n for n in graph.nodes if n.floor == floor]
    positions = [(fn.position.x, fn.position.z) for fn in floor_nodes]

    hazards = []
    for fn in floor_nodes:
        ns = nodes.get(fn.id)
        if ns is None:
            hazards.append(0.0)
        else:
            h = min(1.0, max(0.0,
                     ns.temperature / 400.0 * 0.6 + ns.smoke * 0.4))
            hazards.append(h)

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            gx = -FLOOR_W/2 + (c + 0.5) * (FLOOR_W / GRID_COLS)
            gz = -FLOOR_D/2 + (r + 0.5) * (FLOOR_D / GRID_ROWS)

            total_w = 0.0
            total_v = 0.0
            for i, (px, pz) in enumerate(positions):
                dist = math.hypot(gx - px, gz - pz)
                if dist < 0.01:       # At node position → exact match
                    total_v = hazards[i]
                    total_w = 1.0
                    break
                w = 1.0 / (dist * dist)  # Inverse squared distance
                total_v += hazards[i] * w
                total_w += w

            if total_w > 0:
                grid[r * GRID_COLS + c] = min(1.0, total_v / total_w)

    return grid
```

### Grid Parameters

| Parameter | Value |
|-----------|-------|
| `GRID_COLS` | 32 |
| `GRID_ROWS` | 22 |
| `FLOOR_W` | 40 meters |
| `FLOOR_D` | 28 meters |
| Cell size | 1.25 m × 1.27 m |

The grid is rendered as a `DataTexture` on a `PlaneGeometry` in the Three.js scene, with vertex colors representing hazard intensity.

---

## 11. Diffusion Grid Smoothing

After IDW interpolation, the grid undergoes one pass of **4-neighbor isotropic diffusion** to smooth discontinuities.

### Discrete Laplacian Smoothing

```latex
h^{t+1}(i,j) = min(1.0, (S / W) * (1 + 0.02 * Δt))
```

Where:

```latex
S = 4 * h(i,j) + h(i-1,j) + h(i+1,j) + h(i,j-1) + h(i,j+1)
W = 8  (self × 4 + four neighbors)
```

### Python Implementation

```python
def diffuse_grid(grid, dt=0.5):
    next_grid = [0.0] * (GRID_COLS * GRID_ROWS)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            i = r * GRID_COLS + c
            s = grid[i] * 4        # Self-weight × 4
            w = 4
            if c > 0:              # Left neighbor
                s += grid[i - 1]
                w += 1
            if c < GRID_COLS - 1:  # Right neighbor
                s += grid[i + 1]
                w += 1
            if r > 0:              # Top neighbor
                s += grid[i - GRID_COLS]
                w += 1
            if r < GRID_ROWS - 1:  # Bottom neighbor
                s += grid[i + GRID_COLS]
                w += 1
            next_grid[i] = min(1.0, (s / w) * (1 + 0.02 * dt))
    return next_grid
```

### Properties

| Property | Value |
|----------|-------|
| Neighbor kernel | 4-connected (von Neumann) |
| Self-weight | 4× neighbor weight |
| Growth factor | 1 + 0.02 × Δt (~1% per tick) |
| Clamp | [0, 1] |
| Time step Δt | 0.5 seconds |

The growth factor `(1 + 0.02 * Δt)` models hazard intensification over time: even without new fire injections, existing hazard slowly increases, simulating smoldering spread.

### Diffusion Kernel Visualization

```latex
        0    1    0
K =    1    4    1
        0    1    0       (× 1/8 normalization)

Effective update:
  h_new(i,j) = (4*h(i,j) + h(i-1,j) + h(i+1,j) + h(i,j-1) + h(i,j+1)) / 8
```

---

## Summary of Key Mathematical Constants

```latex
Edge Cost:        C = d * exp(2.2*T_n + 1.6*S_n) + 0.5*O_n*d
                              × (1e6 if flame else 1)

EWMA:             y_t = 0.3*x_t + 0.7*y_{t-1}

Rate Detect:      trigger if |rate| ≥ threshold for 2 consecutive samples

Dijkstra:         O(V²) with linear scan, V = MAX_NODES = 15

IDW:              w_i = 1 / d²(p_g, p_i)

Diffusion:        h_new = (4h_self + Σ h_neighbor) / 8 × 1.01

Shelter:          C_min ≥ 100,000

Flame Block:      C *= 1,000,000

Hold-Down:        1800ms debounce on route switches
```
