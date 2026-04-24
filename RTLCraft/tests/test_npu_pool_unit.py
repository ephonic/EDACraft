"""Tests for NeuralAccel PoolEngine hardware module."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.compute.pool_unit import PoolEngine, POOL_MAX, POOL_AVG


def test_pool_instantiation():
    """PoolEngine should instantiate with correct parameters."""
    pool = PoolEngine(data_width=16, addr_width=8)
    assert pool is not None
    assert pool.data_width == 16
    assert pool.addr_width == 8


def test_pool_verilog_generation():
    """PoolEngine should emit valid Verilog."""
    pool = PoolEngine()
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(pool)
    assert "module PoolEngine" in verilog
    assert "clk" in verilog
    assert "rst_n" in verilog


def test_pool_max_2x2():
    """MaxPool 2x2 with stride=2 on a 4x4x1 feature map."""
    pool = PoolEngine(data_width=16, addr_width=8)
    sim = Simulator(pool)
    sim.reset("rst_n")

    # Setup: 4x4 input, 2x2 kernel, stride=2, no padding
    # Input (channel 0): [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]
    # Expected output 2x2: [[6,8],[14,16]]
    sim.poke("cfg_pool_type", POOL_MAX)
    sim.poke("cfg_kh", 2)
    sim.poke("cfg_kw", 2)
    sim.poke("cfg_stride_h", 2)
    sim.poke("cfg_stride_w", 2)
    sim.poke("cfg_pad_h", 0)
    sim.poke("cfg_pad_w", 0)
    sim.poke("cfg_in_h", 4)
    sim.poke("cfg_in_w", 4)
    sim.poke("cfg_in_c", 1)
    sim.poke("cfg_out_h", 2)
    sim.poke("cfg_out_w", 2)
    sim.poke("cfg_div_shift", 0)
    sim.poke("cfg_src_addr", 0)
    sim.poke("cfg_dst_addr", 100)

    # Write input data to a mock SRAM (simulated via direct pokes on resp)
    input_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    sim.poke("start", 1)
    sim.step()
    sim.poke("start", 0)

    dst_writes = []
    cycle = 0
    max_cycles = 200
    while cycle < max_cycles:
        # If PoolEngine is requesting read, provide data
        if sim.peek("src_req_valid"):
            addr = sim.peek("src_req_addr")
            if 0 <= addr < len(input_data):
                sim.poke("src_resp_data", input_data[addr])
                sim.poke("src_resp_valid", 1)
            else:
                sim.poke("src_resp_valid", 0)
        else:
            sim.poke("src_resp_valid", 0)

        # Capture dst writes
        if sim.peek("dst_req_valid") and sim.peek("dst_req_we"):
            dst_writes.append((sim.peek("dst_req_addr"), sim.peek("dst_req_wdata")))

        sim.step()
        if sim.peek("done"):
            break
        cycle += 1

    assert sim.peek("done") == 1, "PoolEngine did not finish"
    assert len(dst_writes) == 4, f"Expected 4 output writes, got {len(dst_writes)}"

    # Output order: (oh=0,ow=0), (oh=0,ow=1), (oh=1,ow=0), (oh=1,ow=1)
    # Expected: 6, 8, 14, 16
    expected = [6, 8, 14, 16]
    for i, (_, val) in enumerate(dst_writes):
        assert val == expected[i], f"Output {i}: expected {expected[i]}, got {val}"


def test_pool_avg_2x2():
    """AvgPool 2x2 with stride=2 on a 4x4x1 feature map."""
    pool = PoolEngine(data_width=16, addr_width=8)
    sim = Simulator(pool)
    sim.reset("rst_n")

    # Input: [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]
    # Window averages (>>2): 
    #  (0,0): (1+2+5+6)/4 = 14/4 = 3 (with >>2: 14>>2 = 3)
    #  (0,1): (3+4+7+8)/4 = 22/4 = 5 (22>>2 = 5)
    #  (1,0): (9+10+13+14)/4 = 46/4 = 11 (46>>2 = 11)
    #  (1,1): (11+12+15+16)/4 = 54/4 = 13 (54>>2 = 13)
    sim.poke("cfg_pool_type", POOL_AVG)
    sim.poke("cfg_kh", 2)
    sim.poke("cfg_kw", 2)
    sim.poke("cfg_stride_h", 2)
    sim.poke("cfg_stride_w", 2)
    sim.poke("cfg_pad_h", 0)
    sim.poke("cfg_pad_w", 0)
    sim.poke("cfg_in_h", 4)
    sim.poke("cfg_in_w", 4)
    sim.poke("cfg_in_c", 1)
    sim.poke("cfg_out_h", 2)
    sim.poke("cfg_out_w", 2)
    sim.poke("cfg_div_shift", 2)  # divide by 4
    sim.poke("cfg_src_addr", 0)
    sim.poke("cfg_dst_addr", 100)

    input_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    sim.poke("start", 1)
    sim.step()
    sim.poke("start", 0)

    dst_writes = []
    cycle = 0
    max_cycles = 200
    while cycle < max_cycles:
        if sim.peek("src_req_valid"):
            addr = sim.peek("src_req_addr")
            if 0 <= addr < len(input_data):
                sim.poke("src_resp_data", input_data[addr])
                sim.poke("src_resp_valid", 1)
            else:
                sim.poke("src_resp_valid", 0)
        else:
            sim.poke("src_resp_valid", 0)

        if sim.peek("dst_req_valid") and sim.peek("dst_req_we"):
            dst_writes.append((sim.peek("dst_req_addr"), sim.peek("dst_req_wdata")))

        sim.step()
        if sim.peek("done"):
            break
        cycle += 1

    assert sim.peek("done") == 1
    assert len(dst_writes) == 4

    expected = [3, 5, 11, 13]
    for i, (_, val) in enumerate(dst_writes):
        assert val == expected[i], f"Output {i}: expected {expected[i]}, got {val}"
