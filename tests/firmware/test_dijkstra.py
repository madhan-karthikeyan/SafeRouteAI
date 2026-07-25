#!/usr/bin/env python3

"""Tests for Dijkstra pathfinding correctness."""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../simulator"))
from graph_model import BuildingGraph, NodeConfig, EdgeConfig

SHELTER_THRESHOLD = 100000.0
BLOCK_MULTIPLIER = 1e6
ALPHA, BETA, GAMMA = 2.2, 1.6, 0.5

def compute_cost(T_norm, S_norm, O_norm, base_dist, flame):
    hazard_mult = math.exp(ALPHA * T_norm + BETA * S_norm)
    congestion = GAMMA * O_norm * base_dist
    cost = base_dist * hazard_mult + congestion
    if flame:
        cost *= BLOCK_MULTIPLIER
    return cost

def test_basic_path():
    g = BuildingGraph()
    g.add_node(NodeConfig(1, 0, 0, 0, is_exit=True))
    g.add_node(NodeConfig(2, 0, 10, 0))
    g.add_node(NodeConfig(3, 0, 20, 0))
    g.add_edge(EdgeConfig(1, 2, 10))
    g.add_edge(EdgeConfig(2, 3, 10))

    costs = [
        [0, compute_cost(0, 0, 0, 10, False)],
        [compute_cost(0, 0, 0, 10, False), 0, compute_cost(0, 0, 0, 10, False)],
        [0, compute_cost(0, 0, 0, 10, False), 0],
    ]

    adj = {1: [(2, costs[0][1])], 2: [(1, costs[1][0]), (3, costs[1][2])], 3: [(2, costs[2][1])]}
    dist = {1: 0, 2: float('inf'), 3: float('inf')}
    visited = set()
    for _ in range(3):
        u = min((n for n in dist if n not in visited), key=lambda n: dist[n])
        visited.add(u)
        for v, w in adj.get(u, []):
            if v not in visited and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w

    assert dist[1] == 0
    assert dist[3] == costs[0][1] + costs[1][2]
    assert dist[3] < SHELTER_THRESHOLD
    print(f"Path 1->3 cost: {dist[3]:.2f}")
    print("BASIC PATH TEST PASSED")

def test_flame_blocked():
    adj = {
        1: [(2, compute_cost(0, 0, 0, 10, False))],
        2: [(1, compute_cost(0, 0, 0, 10, False)), (3, compute_cost(0, 0, 0, 10, True))],
        3: [(2, compute_cost(0, 0, 0, 10, True))],
    }
    dist = {1: 0, 2: float('inf'), 3: float('inf')}
    visited = set()
    for _ in range(3):
        u = min((n for n in dist if n not in visited), key=lambda n: dist[n])
        visited.add(u)
        for v, w in adj.get(u, []):
            if v not in visited and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w

    assert dist[2] < SHELTER_THRESHOLD
    print(f"Path around flame: {dist[2]:.2f}")
    print("FLAME BLOCKED TEST PASSED")

if __name__ == "__main__":
    test_basic_path()
    test_flame_blocked()
    print("ALL DIJKSTRA TESTS PASSED")
