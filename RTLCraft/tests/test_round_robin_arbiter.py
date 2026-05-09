#!/usr/bin/env python3
"""
8-input Round-Robin Arbiter functional tests.

Covers:
- Reset behavior
- No-request idle state
- Single-request rotation (end-to-end tick)
- Combinatorial logic for all (pointer, reqs) states
- Pointer update sequencing with multiple simultaneous requests
"""

import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import Simulator
from rtlgen.lib import RoundRobinArbiter


def _tick(sim):
    # In this Simulator each step() evaluates sequential logic once,
    # so a single step() is equivalent to one clock cycle.
    sim.step()


def expected_grant(pointer, reqs):
    """Compute expected one-hot grant for a given pointer and reqs."""
    if reqs == 0:
        return 0
    for offset in range(8):
        idx = (pointer + offset) & 0x7
        if (reqs >> idx) & 1:
            return 1 << idx
    return 0


@pytest.fixture
def sim():
    dut = RoundRobinArbiter(req_count=8)
    s = Simulator(dut)
    s.set("rst", 1)
    _tick(s)
    s.set("rst", 0)
    s.set("reqs", 0)
    return s


def test_reset():
    """Assert reset brings pointer to 0 and grants to 0."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    sim.set("reqs", 0)
    _tick(sim)
    assert sim.get_int("pointer") == 0
    assert sim.get_int("grant_vec") == 0
    assert sim.get_int("grants") == 0


def test_no_request(sim):
    """With reqs=0, grants and pointer should remain unchanged."""
    sim.set("reqs", 0)
    for _ in range(10):
        ptr_before = sim.get_int("pointer")
        _tick(sim)
        assert sim.get_int("grants") == 0
        assert sim.get_int("grant_vec") == 0
        assert sim.get_int("pointer") == ptr_before


def test_single_request_rotation():
    """Drive one-hot reqs sequentially and verify round-robin pointer advancement."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    _tick(sim)
    sim.set("rst", 0)

    for i in range(8):
        sim.set("reqs", 1 << i)
        _tick(sim)
        assert sim.get_int("grants") == (1 << i)
        assert sim.get_int("pointer") == ((i + 1) & 0x7)


def test_single_request_wraparound():
    """Drive only req 7 repeatedly; pointer should wrap from 7 back to 0."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    _tick(sim)
    sim.set("rst", 0)

    sim.set("reqs", 1 << 7)
    _tick(sim)
    assert sim.get_int("grants") == (1 << 7)
    assert sim.get_int("pointer") == 0


def test_comb_all_states():
    """Exhaustively verify combinatorial grant for every pointer/reqs pair.

    Uses Simulator._eval_comb() directly so the pointer does not advance.
    """
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    _tick(sim)
    sim.set("rst", 0)

    for pointer in range(8):
        for reqs in range(1 << 8):
            sim.set("pointer", pointer)
            sim.set("reqs", reqs)
            sim._eval_comb()
            actual = sim.get_int("grants")
            exp = expected_grant(pointer, reqs)
            assert actual == exp, (
                f"pointer={pointer}, reqs={reqs:08b}: "
                f"grants={actual:08b}, expected={exp:08b}"
            )


def test_pointer_update_with_multiple_requests():
    """Verify pointer advances to (grant_idx + 1) when multiple reqs are active."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    _tick(sim)
    sim.set("rst", 0)

    # pointer=0, reqs=0b00001111 -> grant should be req0, pointer -> 1
    sim.set("pointer", 0)
    sim.set("reqs", 0b00001111)
    _tick(sim)
    assert sim.get_int("pointer") == 1

    # pointer=1, reqs=0b00001111 -> grant should be req1, pointer -> 2
    sim.set("reqs", 0b00001111)
    _tick(sim)
    assert sim.get_int("pointer") == 2

    # pointer=5, reqs=0b11100000 -> grant should be req5, pointer -> 6
    sim.set("pointer", 5)
    sim.set("reqs", 0b11100000)
    _tick(sim)
    assert sim.get_int("pointer") == 6

    # pointer=6, reqs=0b11100000 -> grant should be req6, pointer -> 7
    sim.set("reqs", 0b11100000)
    _tick(sim)
    assert sim.get_int("pointer") == 7

    # pointer=7, reqs=0b11100000 -> grant should be req7, pointer -> 0
    sim.set("reqs", 0b11100000)
    _tick(sim)
    assert sim.get_int("pointer") == 0

    # pointer=0, reqs=0b11100000 -> grant should be req5, pointer -> 6
    sim.set("reqs", 0b11100000)
    _tick(sim)
    assert sim.get_int("pointer") == 6


def test_all_requests_active():
    """With all reqs active, each tick advances pointer by one."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    sim.set("rst", 1)
    _tick(sim)
    sim.set("rst", 0)

    sim.set("reqs", 0xFF)
    for i in range(16):
        _tick(sim)
        # grants reflects the new pointer after the tick
        assert sim.get_int("pointer") == ((i + 1) & 0x7)


def test_comb_no_reqs():
    """When reqs==0, grants should be 0 for any pointer."""
    dut = RoundRobinArbiter(req_count=8)
    sim = Simulator(dut)
    for pointer in range(8):
        sim.set("pointer", pointer)
        sim.set("reqs", 0)
        sim._eval_comb()
        assert sim.get_int("grants") == 0
