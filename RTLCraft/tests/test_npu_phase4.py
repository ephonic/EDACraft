"""Phase 4 tests: NPU crossbar data movement."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.datapath.crossbar import Crossbar, MODE_BLOCK, MODE_STRIDE, MODE_BROADCAST, MODE_GATHER


def _setup_crossbar():
    """Helper to create and reset a Crossbar."""
    cb = Crossbar(num_ports=4, data_width=16, addr_width=8)
    sim = Simulator(cb)
    sim.reset('rst_n')
    return cb, sim


def test_crossbar_block_mode():
    """Crossbar BLOCK mode should copy contiguous words."""
    cb, sim = _setup_crossbar()

    # Configure: copy 4 words from port 0 addr 0 to port 1 addr 10
    sim.poke('cfg_valid', 1)
    sim.poke('cfg_mode', MODE_BLOCK)
    sim.poke('cfg_src', 0)
    sim.poke('cfg_dst', 1)
    sim.poke('cfg_len', 4)
    sim.poke('cfg_src_addr', 0)
    sim.poke('cfg_dst_addr', 10)
    sim.poke('cfg_stride', 1)
    sim.step()
    sim.poke('cfg_valid', 0)

    # After cfg step: state=READ, src addr = 0
    assert sim.peek('state') == 1  # CB_READ
    assert sim.peek('busy') == 1

    # Step through all 4 words (READ→WRITE per word, last WRITE→DONE)
    expected_addrs = [(0, 10), (1, 11), (2, 12), (3, 13)]
    for i, (src_addr, dst_addr) in enumerate(expected_addrs):
        # READ cycle: provide data
        sim.poke('port_rdata_0', 0x1000 + i)
        sim.step()
        # Now in WRITE cycle: verify read_data latched
        assert sim.peek('read_data') == (0x1000 + i), f"word {i} read_data mismatch"

        # WRITE cycle
        sim.step()
        # After WRITE, either READ (more words) or DONE (last word)
        if i < 3:
            assert sim.peek('state') == 1, f"word {i} should return to READ"
        else:
            assert sim.peek('state') == 3, f"word {i} should be DONE"

    assert sim.peek('done') == 1
    assert sim.peek('busy') == 1  # DONE is not IDLE
    sim.step()  # DONE → IDLE
    assert sim.peek('busy') == 0
    assert sim.peek('done') == 0


def test_crossbar_stride_mode():
    """Crossbar STRIDE mode should copy with stride."""
    cb, sim = _setup_crossbar()

    sim.poke('cfg_valid', 1)
    sim.poke('cfg_mode', MODE_STRIDE)
    sim.poke('cfg_src', 2)
    sim.poke('cfg_dst', 3)
    sim.poke('cfg_len', 3)
    sim.poke('cfg_src_addr', 0)
    sim.poke('cfg_dst_addr', 0)
    sim.poke('cfg_stride', 4)
    sim.step()
    sim.poke('cfg_valid', 0)

    expected_src = [0, 4, 8]
    for i in range(3):
        sim.poke('port_rdata_2', 0x2000 + i)
        sim.step()
        assert sim.peek('read_data') == (0x2000 + i)
        assert sim.peek('src_addr_reg') == expected_src[i]
        sim.step()

    assert sim.peek('done') == 1


def test_crossbar_broadcast_mode():
    """Crossbar BROADCAST mode should copy same src to all dst."""
    cb, sim = _setup_crossbar()

    sim.poke('cfg_valid', 1)
    sim.poke('cfg_mode', MODE_BROADCAST)
    sim.poke('cfg_src', 0)
    sim.poke('cfg_dst', 1)
    sim.poke('cfg_len', 3)
    sim.poke('cfg_src_addr', 5)
    sim.poke('cfg_dst_addr', 0)
    sim.poke('cfg_stride', 1)
    sim.step()
    sim.poke('cfg_valid', 0)

    # Broadcast: src_addr stays at 5, dst_addr advances
    sim.poke('port_rdata_0', 0xBEEF)
    for i in range(3):
        sim.step()  # READ
        assert sim.peek('src_addr_reg') == 5, f"broadcast src addr should stay at 5"
        assert sim.peek('read_data') == 0xBEEF
        sim.step()  # WRITE
        assert sim.peek('dst_addr_reg') == (i + 1)

    assert sim.peek('done') == 1


def test_crossbar_idle_after_done():
    """Crossbar should return to IDLE after DONE."""
    cb, sim = _setup_crossbar()

    assert sim.peek('busy') == 0
    assert sim.peek('done') == 0

    sim.poke('cfg_valid', 1)
    sim.poke('cfg_mode', MODE_BLOCK)
    sim.poke('cfg_src', 0)
    sim.poke('cfg_dst', 1)
    sim.poke('cfg_len', 1)
    sim.poke('cfg_src_addr', 0)
    sim.poke('cfg_dst_addr', 0)
    sim.poke('cfg_stride', 1)
    sim.step()
    sim.poke('cfg_valid', 0)

    assert sim.peek('busy') == 1

    sim.poke('port_rdata_0', 0xABCD)
    sim.step()  # READ
    sim.step()  # WRITE → DONE

    assert sim.peek('done') == 1
    sim.step()  # DONE → IDLE
    assert sim.peek('busy') == 0
    assert sim.peek('done') == 0


def test_crossbar_verilog():
    """Crossbar should emit valid Verilog."""
    cb = Crossbar(num_ports=4, data_width=16, addr_width=8)
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(cb)
    assert "module Crossbar" in verilog
    assert "port_addr_0" in verilog
