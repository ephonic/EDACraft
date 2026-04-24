"""Phase 2 tests: NPU memory layer (PingPongSRAM + Scratchpad)."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.memory.ping_pong_sram import PingPongSRAM
from skills.cpu.npu.memory.scratchpad import Scratchpad


# ---------------------------------------------------------------------------
# Scratchpad tests
# ---------------------------------------------------------------------------

def test_scratchpad_write_read():
    """Scratchpad should support write-then-read."""
    sp = Scratchpad(width=16, depth=16)
    sim = Simulator(sp)
    sim.reset('rst_n')

    # Write 0xABCD to addr 5
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 5)
    sim.poke('req_wdata', 0xABCD)
    sim.poke('req_we', 1)
    sim.step()

    # Read back addr 5
    sim.poke('req_we', 0)
    sim.step()
    assert sim.peek('resp_valid') == 1
    assert sim.peek('resp_data') == 0xABCD


def test_scratchpad_multiple_writes():
    """Scratchpad should store multiple values."""
    sp = Scratchpad(width=16, depth=16)
    sim = Simulator(sp)
    sim.reset('rst_n')

    # Write several values
    for addr, data in [(0, 0x1111), (1, 0x2222), (2, 0x3333), (3, 0x4444)]:
        sim.poke('req_valid', 1)
        sim.poke('req_addr', addr)
        sim.poke('req_wdata', data)
        sim.poke('req_we', 1)
        sim.step()

    # Read them back
    sim.poke('req_we', 0)
    for addr, expected in [(0, 0x1111), (1, 0x2222), (2, 0x3333), (3, 0x4444)]:
        sim.poke('req_addr', addr)
        sim.step()
        assert sim.peek('resp_data') == expected, f"addr={addr} expected={expected:#x} got={sim.peek('resp_data'):#x}"


def test_scratchpad_read_before_write():
    """Uninitialized reads should return 0."""
    sp = Scratchpad(width=16, depth=16)
    sim = Simulator(sp)
    sim.reset('rst_n')

    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0)
    sim.poke('req_we', 0)
    sim.step()
    assert sim.peek('resp_data') == 0


def test_scratchpad_verilog():
    """Scratchpad should emit valid Verilog."""
    sp = Scratchpad(width=16, depth=16)
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(sp)
    assert "module Scratchpad" in verilog
    assert "mem" in verilog


# ---------------------------------------------------------------------------
# PingPongSRAM tests
# ---------------------------------------------------------------------------

def test_pingpong_write_read_bank0():
    """PingPongSRAM bank0 should work before swap."""
    pp = PingPongSRAM(width=16, depth=16)
    sim = Simulator(pp)
    sim.reset('rst_n')

    assert sim.peek('active_bank') == 0

    # Write to bank 0
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 3)
    sim.poke('req_wdata', 0xBEEF)
    sim.poke('req_we', 1)
    sim.poke('bank_swap', 0)
    sim.step()

    # Read back from bank 0
    sim.poke('req_we', 0)
    sim.step()
    assert sim.peek('resp_data') == 0xBEEF


def test_pingpong_bank_swap():
    """Bank swap should toggle active bank."""
    pp = PingPongSRAM(width=16, depth=16)
    sim = Simulator(pp)
    sim.reset('rst_n')

    assert sim.peek('active_bank') == 0

    # Write to bank 0
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0)
    sim.poke('req_wdata', 0xAAAA)
    sim.poke('req_we', 1)
    sim.poke('bank_swap', 0)
    sim.step()

    # Swap to bank 1
    sim.poke('req_we', 0)
    sim.poke('bank_swap', 1)
    sim.step()
    sim.poke('bank_swap', 0)

    assert sim.peek('active_bank') == 1

    # Write different value to bank 1, same address
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0)
    sim.poke('req_wdata', 0xBBBB)
    sim.poke('req_we', 1)
    sim.step()

    # Read back from bank 1
    sim.poke('req_we', 0)
    sim.step()
    assert sim.peek('resp_data') == 0xBBBB

    # Swap back to bank 0
    sim.poke('bank_swap', 1)
    sim.step()
    sim.poke('bank_swap', 0)

    assert sim.peek('active_bank') == 0

    # Read from bank 0 - should still have original value
    sim.poke('req_addr', 0)
    sim.step()
    assert sim.peek('resp_data') == 0xAAAA


def test_pingpong_isolation():
    """Writes to one bank should not affect the other."""
    pp = PingPongSRAM(width=16, depth=16)
    sim = Simulator(pp)
    sim.reset('rst_n')

    # Write to bank 0
    for addr, data in [(0, 0x1111), (1, 0x2222)]:
        sim.poke('req_valid', 1)
        sim.poke('req_addr', addr)
        sim.poke('req_wdata', data)
        sim.poke('req_we', 1)
        sim.step()

    # Swap to bank 1
    sim.poke('req_we', 0)
    sim.poke('bank_swap', 1)
    sim.step()
    sim.poke('bank_swap', 0)

    # Write to bank 1
    for addr, data in [(0, 0x3333), (1, 0x4444)]:
        sim.poke('req_valid', 1)
        sim.poke('req_addr', addr)
        sim.poke('req_wdata', data)
        sim.poke('req_we', 1)
        sim.step()

    # Read bank 1
    sim.poke('req_we', 0)
    for addr, expected in [(0, 0x3333), (1, 0x4444)]:
        sim.poke('req_addr', addr)
        sim.step()
        assert sim.peek('resp_data') == expected

    # Swap back to bank 0
    sim.poke('bank_swap', 1)
    sim.step()
    sim.poke('bank_swap', 0)

    # Read bank 0 - original values intact
    for addr, expected in [(0, 0x1111), (1, 0x2222)]:
        sim.poke('req_addr', addr)
        sim.step()
        assert sim.peek('resp_data') == expected


def test_pingpong_verilog():
    """PingPongSRAM should emit valid Verilog."""
    pp = PingPongSRAM(width=16, depth=16)
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(pp)
    assert "module PingPongSRAM" in verilog
    assert "bank0" in verilog
    assert "bank1" in verilog
