#!/usr/bin/env python3

"""End-to-end scenario tests for SafeRouteAI."""

import sys
import os
import time
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from simulator.injector import Injector, crc16, HAZARD_PACKET_FMT, build_hazard_packet

HAZARD_PACKET_SIZE = struct.calcsize(HAZARD_PACKET_FMT)

def packet_crc_valid(pkt_bytes):
    """Validate CRC the same way the firmware does."""
    if len(pkt_bytes) < 2:
        return False
    data = pkt_bytes[:-2]
    stored_crc = struct.unpack('<H', pkt_bytes[-2:])[0]
    computed = crc16(data)
    return computed == stored_crc

def test_corrupt_packet_rejected():
    inject = Injector()
    node = inject.graph.nodes[0]
    pkt = inject.packet_for_node(node.node_id)
    assert len(pkt) == HAZARD_PACKET_SIZE, f"Expected {HAZARD_PACKET_SIZE}B, got {len(pkt)}B"

    assert packet_crc_valid(pkt), "Valid packet should have correct CRC"
    print("CORRUPT PACKET TEST: valid packet CRC check PASSED")

    inject.set_corrupt_mode(True)
    corrupt_pkt = inject.packet_for_node(node.node_id)
    assert not packet_crc_valid(corrupt_pkt), "Corrupt packet should have invalid CRC"
    print("CORRUPT PACKET TEST: corrupt packet CRC check PASSED")
    inject.set_corrupt_mode(False)

def test_shelter_in_place_trigger():
    inject = Injector()
    inject.set_profile("flashover")
    node_id = 3

    inject.trigger_flashover(node_id)
    time.sleep(0.1)
    future_time = time.time() + 10
    readings = inject.get_readings(node_id, now=future_time)

    assert readings["flame_detected"], "Flashover should trigger flame"
    assert readings["temp_c"] > 100, f"Flashover temp should be high: {readings['temp_c']}"
    assert readings["edge_cost"] >= 100000, f"Edge cost should exceed shelter threshold: {readings['edge_cost']}"
    print(f"SHELTER TEST: Node {node_id} edge_cost={readings['edge_cost']:.0f}, flame={readings['flame_detected']}")
    print("SHELTER-IN-PLACE TEST: PASSED")

def test_fire_profiles():
    from simulator.fire_profiles.slow_smolder import SlowSmolderProfile
    from simulator.fire_profiles.flashover import FlashoverProfile

    slow = SlowSmolderProfile()
    slow.start()
    r = slow.get_readings(time.time() + 60)
    assert r["temp_c"] > 50, f"Slow smolder should rise: {r['temp_c']}"

    fast = FlashoverProfile()
    fast.start()
    r = fast.get_readings(time.time() + 10)
    assert r["temp_c"] > 100, f"Flashover should spike: {r['temp_c']}"
    assert r["flame_detected"], "Flashover should detect flame"
    print("FIRE PROFILES TEST: PASSED")

def test_graph_model():
    from simulator.graph_model import BuildingGraph

    g = BuildingGraph().build_default()
    assert len(g.nodes) >= 6, f"Default graph should have 6+ nodes: {len(g.nodes)}"
    assert len(g.edges) >= 8, f"Default graph should have 8+ edges: {len(g.edges)}"

    d = g.to_dict()
    g2 = BuildingGraph.from_dict(d)
    assert len(g2.nodes) == len(g.nodes)
    assert len(g2.edges) == len(g.edges)
    print("GRAPH MODEL TEST: PASSED")

if __name__ == "__main__":
    test_graph_model()
    test_fire_profiles()
    test_corrupt_packet_rejected()
    test_shelter_in_place_trigger()
    print("\n=== ALL INTEGRATION TESTS PASSED ===")
