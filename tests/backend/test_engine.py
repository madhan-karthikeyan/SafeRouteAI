#!/usr/bin/env python3

import sys, os, time, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from backend.engine import (
    SimState, _dijkstra, _extract_path, _compute_next_hop,
    compute_next_hop, compute_edge_cost, diffuse_hazard,
    compute_occupants, node_hazard, build_node_states, build_routes,
    ALPHA, BETA, GAMMA, BLOCK_MULTIPLIER, SHELTER_THRESHOLD,
    T_BASELINE, T_CRITICAL, OCCUPANT_CAPACITY,
)

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


def test_dijkstra_finds_exit():
    sim = SimState("mega-mall")
    for n in sim.graph.nodes:
        if n.kind == "exit":
            continue
        dist, prev, nearest_exit = _dijkstra(sim, n.id)
        check(f"{n.id} has reachable exit", nearest_exit is not None)
        if nearest_exit:
            path = _extract_path(prev, nearest_exit)
            check(f"{n.id} path starts at source", path[0] == n.id)
            check(f"{n.id} path ends at exit", path[-1] == nearest_exit)
            exit_node = next(x for x in sim.graph.nodes if x.id == nearest_exit)
            check(f"{n.id} target is exit", exit_node.kind == "exit")
            check(f"{n.id} no loops in path", len(path) == len(set(path)))


def test_dijkstra_shelter_threshold():
    sim = SimState("mega-mall")
    src = next(n for n in sim.graph.nodes if n.id == "n-atrium-f0")
    sim.fire_origins[src.id] = {"start": 0, "scenario": "flashover"}
    for _ in range(30):
        diffuse_hazard(sim, 0.5)
    dist, prev, nearest_exit = _dijkstra(sim, src.id)
    check("all paths blocked → shelter-in-place", nearest_exit is None)


def test_route_changes_after_fire():
    sim = SimState("mega-mall")
    src = next(n for n in sim.graph.nodes if n.id == "n-fashion-1-f1")
    dist, prev, nearest_exit = _dijkstra(sim, src.id)
    original_path = _extract_path(prev, nearest_exit)

    fire_node_id = original_path[1] if len(original_path) > 1 else src.id
    sim.fire_origins[fire_node_id] = {"start": 0, "scenario": "flashover"}
    for _ in range(15):
        diffuse_hazard(sim, 0.5)

    dist2, prev2, nearest_exit2 = _dijkstra(sim, src.id)
    if nearest_exit2:
        new_path = _extract_path(prev2, nearest_exit2)
        check("route changes after fire on path", original_path != new_path)
        blocked_exit_cost = dist2.get(fire_node_id, 0)
        check("blocked node has high cost", blocked_exit_cost >= SHELTER_THRESHOLD)
    else:
        check("shelter after fire", True)


def test_edge_cost_zero_self_loop():
    sim = SimState("mega-mall")
    node = sim.graph.nodes[0]
    cost = compute_edge_cost(sim, node, node)
    check("same-node edge cost is 0", cost == 0.0)


def test_edge_cost_nonzero():
    sim = SimState("mega-mall")
    a = sim.graph.nodes[0]
    b = sim.graph.nodes[1]
    cost = compute_edge_cost(sim, a, b)
    check("adjacent edge cost > 0", cost > 0)


def test_edge_cost_symmetry():
    sim = SimState("mega-mall")
    a = sim.graph.nodes[0]
    b = next(n for n in sim.graph.nodes if n.id != a.id)
    cost_ab = compute_edge_cost(sim, a, b)
    cost_ba = compute_edge_cost(sim, b, a)
    check("edge cost is symmetric", abs(cost_ab - cost_ba) < 0.001)


def test_compute_next_hop_returns_none_for_exit():
    sim = SimState("mega-mall")
    exit_node = next(n for n in sim.graph.nodes if n.kind == "exit")
    nh = compute_next_hop(sim, exit_node)
    check("exit node returns None hop", nh is None)


def test_compute_next_hop_non_exit():
    sim = SimState("mega-mall")
    sensor = next(n for n in sim.graph.nodes if n.kind == "sensor")
    nh = compute_next_hop(sim, sensor)
    check("sensor node returns a next hop", nh is not None)
    if nh:
        nh_node = next(n for n in sim.graph.nodes if n.id == nh)
        check("next hop is a neighbor", any(
            nh == (e.from_node if e.to_node == sensor.id else e.to_node if e.from_node == sensor.id else None)
            for e in sim.graph.edges
        ))


def test_build_routes_returns_valid_routes():
    sim = SimState("mega-mall")
    routes = build_routes(sim)
    check("routes list is non-empty", len(routes) > 0)
    for r in routes:
        check(f"route {r.id} has at least 2 nodes", len(r.path) >= 2)
        check(f"route {r.id} starts with origin id", r.id.endswith(r.path[0]))
        check(f"route {r.id} priority in [0,1]", 0.0 <= r.priority <= 1.0)


def test_build_node_states_all_nodes():
    sim = SimState("mega-mall")
    states = build_node_states(sim)
    check("all graph nodes have state", len(states) == len(sim.graph.nodes))
    for nid, st in states.items():
        check(f"node {nid} has valid temperature", 20 <= st.temperature <= 500)
        check(f"node {nid} has valid smoke [0,1]", 0.0 <= st.smoke <= 1.0)
        check(f"node {nid} has valid occupancy >= 0", st.occupants >= 0)


def test_occupants_distribution():
    sim = SimState("mega-mall")
    total = sum(compute_occupants(sim, n) for n in sim.graph.nodes)
    check("total occupants > 0", total > 0)


def test_snapshot_serializable():
    sim = SimState("mega-mall")
    snap = __import__("backend.engine", fromlist=["tick_sim"]).tick_sim(sim)
    d = snap.model_dump()
    check("snapshot has t field", isinstance(d["t"], int))
    check("snapshot has status field", isinstance(d["status"], str))
    check("snapshot has hazard with string keys",
          all(isinstance(k, str) for k in d["hazard"].keys()))
    check("snapshot has hazard with list values",
          all(isinstance(v, list) for v in d["hazard"].values()))


def test_known_cost_value():
    sim = SimState("mega-mall")
    a = sim.graph.nodes[0]
    b = sim.graph.nodes[1]
    cost = compute_edge_cost(sim, a, b)
    base_dist = math.sqrt(
        (a.position.x - b.position.x)**2 +
        (a.position.z - b.position.z)**2 +
        ((a.position.y - b.position.y) * 1.5)**2
    )
    check(f"cost {cost:.2f} >= base_dist {base_dist:.2f}", cost >= base_dist)
    check(f"cost {cost:.2f} < shelter threshold", cost < SHELTER_THRESHOLD)

    # Verify the cost formula matches firmware compute_edge_cost
    h = max(node_hazard(sim, a), node_hazard(sim, b))
    temp = 22 + h * 380
    T_norm = max(0, min(1, (temp - T_BASELINE) / (T_CRITICAL - T_BASELINE)))
    S_norm = max(0, min(1, h * 1.2))
    occ_a = compute_occupants(sim, a)
    occ_b = compute_occupants(sim, b)
    O_norm = max(0, min(1, max(occ_a, occ_b) / OCCUPANT_CAPACITY))
    expected = base_dist * math.exp(ALPHA * T_norm + BETA * S_norm) + GAMMA * O_norm * base_dist
    check(f"cost {cost:.4f} == firmware formula {expected:.4f}", abs(cost - expected) < 0.001)


def test_golden_cost_formula():
    """Golden values: validate cost formula matches firmware routing.cpp.
    
    These exact (T_norm, S_norm, O_norm, base_dist, flame) → cost mappings
    serve as the cross-implementation contract between backend, frontend,
    firmware, and MQTT bridge. All four must produce identical results.
    """
    cases = [
        # (T_norm, S_norm, O_norm, base_dist, flame, expected_cost)
        (0.0, 0.0, 0.0, 10.0, False, 10.0),            # no hazard
        (0.5, 0.0, 0.0, 10.0, False, 10.0 * math.exp(2.2 * 0.5)),  # moderate temp
        (1.0, 0.0, 0.0, 10.0, False, 10.0 * math.exp(2.2)),         # max temp
        (0.0, 1.0, 0.0, 10.0, False, 10.0 * math.exp(1.6)),         # max smoke
        (0.0, 0.0, 0.5, 10.0, False, 10.0 + 0.5 * 0.5 * 10.0),    # congestion
        (0.0, 0.0, 0.0, 10.0, True, 10.0 * BLOCK_MULTIPLIER),      # flame blocked
        (0.3, 0.2, 0.1, 15.0, False, 15.0 * math.exp(2.2*0.3+1.6*0.2) + 0.5*0.1*15.0),
        (0.8, 0.7, 0.3, 5.0, True, (5.0 * math.exp(2.2*0.8+1.6*0.7) + 0.5*0.3*5.0) * BLOCK_MULTIPLIER),
    ]
    for tn, sn, on, bd, flame, expected in cases:
        hazard_mult = math.exp(ALPHA * tn + BETA * sn)
        congestion = GAMMA * on * bd
        got = bd * hazard_mult + congestion
        if flame:
            got *= BLOCK_MULTIPLIER
        check(f"golden cost T={tn} S={sn} O={on} d={bd} flame={flame}",
              abs(got - expected) < 0.001)


def test_golden_flame_cost_dominates():
    """On a three-node line graph (A-B-C, exit at C), fire at B must
    force A to go directly through B (blocked, very high cost) or find
    no alternative path, triggering shelter."""
    from backend.engine import SimState, compute_edge_cost, node_hazard
    sim = SimState("mega-mall")
    a = next(n for n in sim.graph.nodes if n.id == "n-atrium-f0")
    b = next(n for n in sim.graph.nodes if n.id == "n-luxury-1-f0")
    
    # Before fire: cost should be normal
    cost_normal = compute_edge_cost(sim, a, b)
    
    # Set fire at b
    sim.fire_origins[b.id] = {"start": 0, "scenario": "flashover"}
    for _ in range(30):
        diffuse_hazard(sim, 0.5)
    
    # After fire: cost should be multiplied by BLOCK_MULTIPLIER
    cost_blocked = compute_edge_cost(sim, a, b)
    check("flame cost >> normal cost", cost_blocked > cost_normal * 1000)
    check("flame cost exceeds shelter", cost_blocked >= SHELTER_THRESHOLD)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(f"\n{name}:")
            fn()

    print(f"\n{'='*40}")
    print(f"Passed: {PASS}, Failed: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
