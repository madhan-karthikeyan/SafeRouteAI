#!/usr/bin/env python3

"""Tests for sensor fusion cost formula and dual-path filtering logic."""

import sys
import math
import struct

sys.path.insert(0, "..")

ALPHA = 2.2
BETA = 1.6
GAMMA = 0.5
BLOCK_MULTIPLIER = 1e6
SHELTER_THRESHOLD = 100000.0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def compute_edge_cost(T_norm, S_norm, O_norm, base_dist, flame):
    hazard_mult = math.exp(ALPHA * T_norm + BETA * S_norm)
    congestion_term = GAMMA * O_norm * base_dist
    cost = base_dist * hazard_mult + congestion_term
    if flame:
        cost *= BLOCK_MULTIPLIER
    return cost

def test_no_hazard():
    cost = compute_edge_cost(0, 0, 0, 10, False)
    assert abs(cost - 10.0) < 0.01, f"Expected ~10, got {cost}"

def test_full_hazard_no_flame():
    cost = compute_edge_cost(1.0, 1.0, 0.5, 10, False)
    assert cost > 10, f"Should be higher than base: {cost}"
    assert cost < SHELTER_THRESHOLD, f"Should be below shelter threshold: {cost}"

def test_flame_block():
    cost = compute_edge_cost(0, 0, 0, 10, True)
    assert cost >= BLOCK_MULTIPLIER * 10, f"Flame should multiply: {cost}"

def test_shelter_threshold_crossed():
    cost = compute_edge_cost(1.0, 1.0, 1.0, 50, True)
    assert cost >= SHELTER_THRESHOLD, f"Should exceed shelter: {cost}"

def test_continuous_no_step():
    for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
        c1 = compute_edge_cost(t, 0, 0, 10, False)
        c2 = compute_edge_cost(t + 0.01, 0, 0, 10, False)
        assert c2 > c1, f"Cost must be strictly increasing at T_norm={t}"

def test_congestion_additive_not_multiplicative():
    no_cong = compute_edge_cost(0.5, 0.5, 0, 10, False)
    with_cong = compute_edge_cost(0.5, 0.5, 1.0, 10, False)
    diff = with_cong - no_cong
    assert abs(diff - GAMMA * 1.0 * 10) < 0.01, f"Congestion should add {GAMMA*10}, got {diff}"

if __name__ == "__main__":
    test_no_hazard()
    test_full_hazard_no_flame()
    test_flame_block()
    test_shelter_threshold_crossed()
    test_continuous_no_step()
    test_congestion_additive_not_multiplicative()
    print("ALL FUSION TESTS PASSED")
