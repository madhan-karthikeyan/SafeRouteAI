#!/usr/bin/env python3

"""Tests for sequence number acceptance/rejection logic."""

import sys

last_seq = {}

def seq_num_accept(from_id, seq):
    if from_id in last_seq:
        last_s = last_seq[from_id]
        diff = seq - last_s
        if diff > 0 or (diff < 0 and last_s > 0xF0000000 and seq < 0x0FFFFFFF):
            last_seq[from_id] = seq
            return True
        return False
    else:
        last_seq[from_id] = seq
        return True

def test_accept_new():
    assert seq_num_accept(1, 1)
    assert seq_num_accept(1, 2)
    assert seq_num_accept(1, 3)

def test_reject_old():
    assert not seq_num_accept(1, 2)
    assert not seq_num_accept(1, 1)

def test_accept_after_wraparound():
    last_seq.clear()
    last_seq[2] = 0xFFFFFFF0
    assert seq_num_accept(2, 0x00000005)

def test_accept_same_node():
    last_seq.clear()
    assert seq_num_accept(3, 100)
    assert not seq_num_accept(3, 99)
    assert seq_num_accept(3, 101)

if __name__ == "__main__":
    test_accept_new()
    test_reject_old()
    test_accept_after_wraparound()
    test_accept_same_node()
    print("ALL SEQ_NUM TESTS PASSED")
