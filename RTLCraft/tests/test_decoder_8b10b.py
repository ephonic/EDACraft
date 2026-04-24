#!/usr/bin/env python3
"""
Basic functional tests for the 8b10b decoder.

Covers:
- Reset behavior
- Control symbol decoding (K.28.0, K.28.5, K.23.7, etc.)
- Data symbol decoding (5b/6b + 3b/4b tables)
- 1-cycle latency and valid propagation
"""

import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import Simulator
from examples.decoder_8b10b import Decoder8b10b, CONTROL_TABLE, DATA5_TABLE, DATA3_TABLE


def build_data_lookup():
    """Build a dict for data symbol decoding from 10-bit -> 8-bit."""
    d5 = {}
    for pat, val in DATA5_TABLE:
        d5[pat] = val
    d3 = {}
    for pat, val in DATA3_TABLE:
        d3[pat] = val

    lut = {}
    for upper in range(1 << 6):
        for lower in range(1 << 4):
            ten = (upper << 4) | lower
            if upper in d5 and lower in d3:
                lut[ten] = (d3[lower] << 5) | d5[upper]
    return lut


def build_control_lookup():
    """Build a dict for control symbol decoding from 10-bit -> 8-bit."""
    lut = {}
    for pat, val in CONTROL_TABLE:
        lut[pat] = val
    return lut


DATA_LUT = build_data_lookup()
CONTROL_LUT = build_control_lookup()


def _tick(sim):
    sim.set("clk_in", 0)
    sim.step()
    sim.set("clk_in", 1)
    sim.step()


@pytest.fixture
def sim():
    dut = Decoder8b10b()
    s = Simulator(dut)
    # reset
    s.set("reset_in", 1)
    _tick(s)
    s.set("reset_in", 0)
    s.set("decoder_valid_in", 0)
    s.set("control_in", 0)
    s.set("decoder_in", 0)
    return s


def test_reset(sim):
    sim.set("reset_in", 1)
    _tick(sim)
    assert sim.get_int("decoder_out") == 0
    assert sim.get_int("decoder_valid_out") == 0
    assert sim.get_int("control_out") == 0


def test_control_symbols(sim):
    """Drive each control pattern and verify decoded output after 1 cycle."""
    for pattern, expected in CONTROL_LUT.items():
        sim.set("control_in", 1)
        sim.set("decoder_in", pattern)
        sim.set("decoder_valid_in", 1)
        _tick(sim)
        assert sim.get_int("decoder_valid_out") == 1
        assert sim.get_int("control_out") == 1
        assert sim.get_int("decoder_out") == expected


def test_data_symbols_selected(sim):
    """Drive a few representative data patterns."""
    samples = [
        (0b100111_0100, 0b000_00000),
        (0b011000_1011, 0b000_00000),
        (0b110001_0011, 0b011_00011),
        (0b111000_1110, 0b111_00111),
        (0b101011_0001, 0b111_11111),
    ]
    for ten, expected in samples:
        sim.set("control_in", 0)
        sim.set("decoder_in", ten)
        sim.set("decoder_valid_in", 1)
        _tick(sim)
        assert sim.get_int("decoder_valid_out") == 1
        assert sim.get_int("control_out") == 0
        assert sim.get_int("decoder_out") == expected


def test_data_all_valid_combinations():
    """Exhaustively test all 10-bit words that map in data LUT."""
    dut = Decoder8b10b()
    sim = Simulator(dut)
    sim.set("reset_in", 1)
    _tick(sim)
    sim.set("reset_in", 0)

    for ten, expected in DATA_LUT.items():
        sim.set("control_in", 0)
        sim.set("decoder_in", ten)
        sim.set("decoder_valid_in", 1)
        _tick(sim)
        assert sim.get_int("decoder_valid_out") == 1
        assert sim.get_int("control_out") == 0
        assert sim.get_int("decoder_out") == expected, f"mismatch at 0b{ten:010b}"


def test_valid_latency(sim):
    """Verify that valid propagates with exactly 1-cycle delay."""
    sim.set("decoder_valid_in", 0)
    sim.set("control_in", 0)
    sim.set("decoder_in", 0b100111_0100)
    _tick(sim)
    assert sim.get_int("decoder_valid_out") == 0

    sim.set("decoder_valid_in", 1)
    _tick(sim)
    assert sim.get_int("decoder_valid_out") == 1


def test_invalid_control_fallback(sim):
    """When control_in=1 but pattern is not a known control symbol, output 0."""
    sim.set("control_in", 1)
    sim.set("decoder_in", 0b000000_0000)
    sim.set("decoder_valid_in", 1)
    _tick(sim)
    assert sim.get_int("decoder_valid_out") == 1
    assert sim.get_int("control_out") == 1
    assert sim.get_int("decoder_out") == 0
