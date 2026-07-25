#!/usr/bin/env python3

"""Tests for fire profile curves."""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from simulator.fire_profiles.slow_smolder import SlowSmolderProfile
from simulator.fire_profiles.flashover import FlashoverProfile

def test_slow_smolder_initial():
    p = SlowSmolderProfile()
    p.start()
    r = p.get_readings(p.t0)
    assert abs(r["temp_c"] - 25.0) < 1.0, f"Start temp should be ~25: {r['temp_c']}"
    assert r["smoke_ppm"] < 15, f"Start smoke should be near 0: {r['smoke_ppm']}"
    print(f"  Initial: {r}")

def test_slow_smolder_after_30s():
    p = SlowSmolderProfile()
    p.start()
    r = p.get_readings(p.t0 + 30)
    assert r["temp_c"] > 30, f"Should rise above baseline: {r['temp_c']}"
    assert r["smoke_ppm"] > 50, f"Smoke should be significant: {r['smoke_ppm']}"
    print(f"  After 30s: {r}")

def test_slow_smolder_final():
    p = SlowSmolderProfile()
    p.start()
    r = p.get_readings(p.t0 + 120)
    assert r["temp_c"] > 60, f"Should approach max temp: {r['temp_c']}"
    print(f"  After 120s: {r}")

def test_flashover_initial():
    p = FlashoverProfile()
    p.start()
    r = p.get_readings(p.t0)
    assert abs(r["temp_c"] - 25.0) < 1.0, f"Start temp should be ~25: {r['temp_c']}"
    print(f"  Initial: {r}")

def test_flashover_after_5s():
    p = FlashoverProfile()
    p.start()
    r = p.get_readings(p.t0 + 5)
    assert r["temp_c"] > 100, f"Should spike rapidly: {r['temp_c']}"
    assert r["flame_detected"], "Flame should be detected"
    print(f"  After 5s: {r}")

def test_flashover_final():
    p = FlashoverProfile()
    p.start()
    r = p.get_readings(p.t0 + 20)
    assert r["temp_c"] > 200, f"Should near max temp: {r['temp_c']}"
    assert r["smoke_ppm"] > 2000, f"Smoke should be very high: {r['smoke_ppm']}"
    print(f"  After 20s: {r}")

if __name__ == "__main__":
    print("Slow Smolder Profile:")
    test_slow_smolder_initial()
    test_slow_smolder_after_30s()
    test_slow_smolder_final()

    print("\nFlashover Profile:")
    test_flashover_initial()
    test_flashover_after_5s()
    test_flashover_final()

    print("\nALL PROFILE TESTS PASSED")
