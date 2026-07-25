#!/usr/bin/env python3

"""Tests for hold-down hysteresis logic."""

HOLD_DOWN_MS = 1800

last_switch_ms = 0
initial_path_set = False

def hold_down_should_switch(new_hop, current_hop, new_cost, flame_on_current, now_ms):
    global last_switch_ms, initial_path_set
    if new_hop == 0:
        return False
    if current_hop == 0:
        initial_path_set = True
        last_switch_ms = now_ms
        return True
    if flame_on_current:
        last_switch_ms = now_ms
        return True
    if not initial_path_set:
        initial_path_set = True
        last_switch_ms = now_ms
        return True
    elapsed = now_ms - last_switch_ms
    if elapsed < HOLD_DOWN_MS and new_cost > 0.7 * 1e9:
        return False
    last_switch_ms = now_ms
    return True

def reset_globals():
    global last_switch_ms, initial_path_set
    last_switch_ms = 0
    initial_path_set = False

def test_initial_switch():
    reset_globals()
    assert hold_down_should_switch(2, 0, 100, False, 0)
    assert initial_path_set
    assert last_switch_ms == 0

def test_flame_overrides_hold():
    reset_globals()
    hold_down_should_switch(2, 0, 100, False, 0)
    last_switch_ms = 1000
    initial_path_set = True
    assert hold_down_should_switch(3, 2, 200, True, 1200)

def test_hold_suppresses_small_change():
    reset_globals()
    hold_down_should_switch(2, 0, 100, False, 0)
    last_switch_ms = 100
    result = hold_down_should_switch(4, 2, 0.8 * 1e9, False, 300)
    assert not result, "Should hold during hold-down period"

def test_switch_after_hold_expires():
    reset_globals()
    hold_down_should_switch(2, 0, 100, False, 0)
    last_switch_ms = 100
    result = hold_down_should_switch(4, 2, 0.8 * 1e9, False, 5000)
    assert result, "Should switch after hold-down expires"

if __name__ == "__main__":
    test_initial_switch()
    test_flame_overrides_hold()
    test_hold_suppresses_small_change()
    test_switch_after_hold_expires()
    print("ALL HOLD-DOWN TESTS PASSED")
