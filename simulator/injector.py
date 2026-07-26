#!/usr/bin/env python3

"""
Fire Event Injector for SafeRouteAI.

Broadcasts simulated multi-sensor fire timelines into the MCU network
via serial or MQTT. Supports:
  - Two fire-growth profiles (slow smolder, fast flashover)
  - Judge-triggerable zone/node flashover
  - Corrupt-packet injection mode
  - Live operator CLI
"""

import argparse
import json
import struct
import time
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.graph_model import BuildingGraph
from simulator.fire_profiles.slow_smolder import SlowSmolderProfile
from simulator.fire_profiles.flashover import FlashoverProfile

HAZARD_PACKET_FMT = "<H I I f f ? f H"
HAZARD_PACKET_SIZE = struct.calcsize(HAZARD_PACKET_FMT)

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def build_hazard_packet(node_id: int, seq_num: int, uptime_ms: int,
                         temp_c: float, smoke_ppm: float,
                         flame: bool, edge_cost: float,
                         corrupt: bool = False) -> bytes:
    fmt_no_crc = "<H I I f f ? f"
    data_bytes = struct.pack(fmt_no_crc, node_id, seq_num, uptime_ms,
                              temp_c, smoke_ppm, flame, edge_cost)
    if not corrupt:
        crc = crc16(data_bytes)
    else:
        crc = 0
    data_bytes += struct.pack("<H", crc)
    return data_bytes

class Injector:
    def __init__(self, graph_path: str = None):
        self.graph = BuildingGraph()
        if graph_path:
            self.graph = BuildingGraph.load(graph_path)
        else:
            self.graph.build_default()

        self.profiles = {
            "slow": SlowSmolderProfile(),
            "flashover": FlashoverProfile(),
        }
        self.active_profile = None
        self.profile_name = None
        self.seq = 0
        self.corrupt_mode = False
        self.target_zone = None
        self.running = False

    def set_profile(self, name: str):
        if name in self.profiles:
            self.profile_name = name
            self.active_profile = self.profiles[name]
            self.active_profile.start()
            print(f"Profile set: {name}")
        else:
            print(f"Unknown profile: {name}. Options: {list(self.profiles.keys())}")

    def trigger_flashover(self, zone_id: int):
        self.target_zone = zone_id
        self.set_profile("flashover")
        print(f"FLASHOVER triggered on zone {zone_id}")

    def set_corrupt_mode(self, enabled: bool):
        self.corrupt_mode = enabled
        print(f"Corrupt packet mode: {'ENABLED' if enabled else 'DISABLED'}")

    def get_readings(self, node_id: int, now=None) -> dict:
        base = {"temp_c": 25.0, "smoke_ppm": 0.0, "flame_detected": False}

        if self.target_zone is not None and node_id == self.target_zone and self.active_profile:
            base.update(self.active_profile.get_readings(now=now))

        node = self.graph.find_node(node_id)
        if node:
            T_norm = max(0, min(1, (base["temp_c"] - node.T_baseline) /
                                (node.T_critical - node.T_baseline)))
            S_norm = max(0, min(1, (base["smoke_ppm"] - node.S_baseline) /
                                (node.S_critical - node.S_baseline)))
            O_norm = max(0, min(1, 2.0 / node.occupant_capacity))

            hazard_mult = (2.71828 ** (2.2 * T_norm + 1.6 * S_norm))
            edge_cost = 10.0 * hazard_mult + 0.5 * O_norm * 10.0
            if base["flame_detected"]:
                edge_cost *= 1000000.0
            base["edge_cost"] = round(edge_cost, 2)
        else:
            base["edge_cost"] = 0.0

        return base

    def packet_for_node(self, node_id: int, uptime_ms: int = 0) -> bytes:
        readings = self.get_readings(node_id)
        self.seq += 1
        return build_hazard_packet(
            node_id=node_id,
            seq_num=self.seq,
            uptime_ms=uptime_ms,
            temp_c=readings["temp_c"],
            smoke_ppm=readings["smoke_ppm"],
            flame=readings["flame_detected"],
            edge_cost=readings["edge_cost"],
            corrupt=self.corrupt_mode
        )

    def run_cli(self):
        print("=== SafeRouteAI Injector CLI ===")
        print("Commands: slow | flashover | zone <id> | corrupt | clean | pub | quit")
        self.running = True

        while self.running:
            try:
                cmd = input("inject> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == "quit":
                self.running = False
            elif cmd == "slow":
                self.set_profile("slow")
            elif cmd == "flashover":
                if self.target_zone is None:
                    print("Set a target zone first: zone <id>")
                else:
                    self.trigger_flashover(self.target_zone)
            elif cmd.startswith("zone "):
                try:
                    zid = int(cmd.split()[1])
                    self.target_zone = zid
                    print(f"Target zone set to {zid}")
                except (IndexError, ValueError):
                    print("Usage: zone <id>")
            elif cmd == "corrupt":
                self.set_corrupt_mode(True)
            elif cmd == "clean":
                self.set_corrupt_mode(False)
            elif cmd == "pub":
                if self.target_zone is not None:
                    self.publish_mqtt(self.target_zone)
                    print(f"Published MQTT for zone {self.target_zone}")
                else:
                    for node in self.graph.nodes:
                        self.publish_mqtt(node.node_id)
                    print("Published MQTT for all nodes")
            elif cmd == "":
                continue
            else:
                print(f"Unknown: {cmd}")

    def packet_hex(self, node_id: int) -> str:
        pkt = self.packet_for_node(node_id)
        return pkt.hex()

    def print_packet(self, node_id: int):
        readings = self.get_readings(node_id)
        pkt = self.packet_for_node(node_id)
        fmt_no_crc = "<H I I f f ? f"
        print(f"Packet [{len(pkt)}b]:")
        print(f"  Node ID:    {node_id}")
        print(f"  Temp:       {readings['temp_c']:.1f} C")
        print(f"  Smoke:      {readings['smoke_ppm']:.0f} ppm")
        print(f"  Flame:      {readings['flame_detected']}")
        print(f"  Edge Cost:  {readings['edge_cost']:.2f}")
        payload = pkt[:-2]
        stored_crc = struct.unpack("<H", pkt[-2:])[0]
        computed_crc = crc16(payload)
        print(f"  CRC valid:  {computed_crc == stored_crc} (stored={stored_crc:#x}, computed={computed_crc:#x})")
        print(f"  Hex:        {pkt.hex()}")

def main():
    parser = argparse.ArgumentParser(description="SafeRouteAI Fire Injector")
    parser.add_argument("--graph", help="Path to building graph JSON")
    parser.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    parser.add_argument("--zone", type=int, help="Target zone/node ID")
    parser.add_argument("--profile", choices=["slow", "flashover"], default="slow")
    parser.add_argument("--corrupt", action="store_true", help="Enable corrupt packet mode")
    parser.add_argument("--packet", type=int, help="Generate one packet for given node ID and print")
    parser.add_argument("--mqtt", action="store_true", help="Enable MQTT broadcasting")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    args = parser.parse_args()

    injector = Injector(graph_path=args.graph)

    if args.mqtt:
        injector.connect_mqtt(broker=args.broker)

    if args.packet is not None:
        injector.print_packet(args.packet)
        return

    if args.zone is not None:
        injector.target_zone = args.zone
    injector.set_profile(args.profile)
    injector.set_corrupt_mode(args.corrupt)

    if args.cli:
        injector.run_cli()
    else:
        print("Running injector in single-shot mode.")
        for node in injector.graph.nodes:
            injector.print_packet(node.node_id)
            if args.mqtt:
                injector.publish_mqtt(node.node_id)

if __name__ == "__main__":
    main()
