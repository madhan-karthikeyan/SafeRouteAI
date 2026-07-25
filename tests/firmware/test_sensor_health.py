#!/usr/bin/env python3

"""Tests for three-tier sensor health fail-safe."""

import struct
import math

SENSOR_NOISE_FLOOR = 0.001

class SensorHealth:
    def __init__(self):
        self.ring_buffer = [0.0] * 10
        self.idx = 0
        self.healthy = True
        self.first_sample_ms = 0
        self.last_sample_ms = 0

def compute_variance(buf):
    mean = sum(buf) / len(buf)
    return sum((x - mean) ** 2 for x in buf) / len(buf)

def sensor_health_update(h, sample, phys_min, phys_max, now_ms):
    if math.isnan(sample) or sample < phys_min or sample > phys_max:
        h.healthy = False
        return
    h.ring_buffer[h.idx % 10] = sample
    h.idx += 1
    h.last_sample_ms = now_ms
    if h.idx >= 10 and (h.last_sample_ms - h.first_sample_ms >= 30000):
        var = compute_variance(h.ring_buffer)
        if var < SENSOR_NOISE_FLOOR:
            h.healthy = False
            return
    h.healthy = True

def test_nan_rejected():
    h = SensorHealth()
    sensor_health_update(h, float('nan'), 0, 100, 1000)
    assert not h.healthy

def test_out_of_range_rejected():
    h = SensorHealth()
    sensor_health_update(h, 200, 0, 100, 1000)
    assert not h.healthy

def test_valid_accepted():
    h = SensorHealth()
    for t in range(100, 100100, 100):
        sensor_health_update(h, 25.0 + math.sin(t) * 0.1, -20, 150, t)
    assert h.healthy

def test_stuck_detected():
    h = SensorHealth()
    for t in range(0, 60000, 100):
        sensor_health_update(h, 25.0, -20, 150, t + h.first_sample_ms)
    assert not h.healthy, "Stuck reading should be detected"

if __name__ == "__main__":
    test_nan_rejected()
    test_out_of_range_rejected()
    test_valid_accepted()
    test_stuck_detected()
    print("ALL SENSOR HEALTH TESTS PASSED")
