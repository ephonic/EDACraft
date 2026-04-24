"""
Tests for the GPGPU streaming processor core.

Covers:
  - Module instantiation
  - Verilog code generation
  - Basic port connectivity checks
  - Full-chip functional simulation (ADD + writeback)
"""

import sys
sys.path.insert(0, "g:/code/rtlgen")

import pytest

from rtlgen import VerilogEmitter
from skills.gpgpu.common.params import GPGPUParams
from skills.gpgpu.common import isa
from skills.gpgpu.core.register_file import RegisterFile
from skills.gpgpu.core.alu_array import ALUArray
from skills.gpgpu.core.sfu import SFUArray
from skills.gpgpu.core.tensor_core import TensorCore
from skills.gpgpu.core.warp_scheduler import WarpScheduler
from skills.gpgpu.core.scoreboard import Scoreboard
from skills.gpgpu.core.frontend import Frontend
from skills.gpgpu.core.memory_unit import MemoryCoalescer, L1Cache, SharedMemory
from skills.gpgpu.core.gpgpu_core import GPGPUCore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def params():
    return GPGPUParams()


# ---------------------------------------------------------------------------
# Individual module instantiation tests
# ---------------------------------------------------------------------------
def test_register_file_instantiates(params):
    rf = RegisterFile(params)
    assert rf.name == "RegisterFile"
    assert len(rf.rd_data_a) == params.warp_size


def test_alu_array_instantiates(params):
    alu = ALUArray(params)
    assert alu.name == "ALUArray"
    assert len(alu.result) == params.alu_lanes


def test_sfu_array_instantiates(params):
    sfu = SFUArray(params)
    assert sfu.name == "SFUArray"
    # Current implementation creates one SFU lane per ALU lane (32)
    assert len(sfu.result) == params.alu_lanes


def test_tensor_core_instantiates(params):
    tc = TensorCore(params)
    assert tc.name == "TensorCore"
    assert tc.done.width == 1


def test_warp_scheduler_instantiates(params):
    ws = WarpScheduler(params)
    assert ws.name == "WarpScheduler"
    assert ws.issue_valid.width == 1


def test_scoreboard_instantiates(params):
    sb = Scoreboard(params)
    assert sb.name == "Scoreboard"
    assert sb.issue_ready.width == 1


def test_frontend_instantiates(params):
    fe = Frontend(params)
    assert fe.name == "Frontend"
    assert fe.dec_opcode.width == 6


def test_memory_coalescer_instantiates(params):
    mc = MemoryCoalescer(params)
    assert mc.name == "MemoryCoalescer"
    assert len(mc.out_data) == mc.words_per_req


def test_l1_cache_instantiates(params):
    cache = L1Cache(params)
    assert cache.name == "L1Cache"
    assert cache.hit.width == 1


def test_shared_memory_instantiates(params):
    smem = SharedMemory(params)
    assert smem.name == "SharedMemory"
    assert smem.rd_data.width == params.data_width


# ---------------------------------------------------------------------------
# Top-level integration test
# ---------------------------------------------------------------------------
def test_gpgpu_core_instantiates(params):
    core = GPGPUCore(params)
    assert core.name == "GPGPUCore"
    assert core.launch_valid.width == 1


# ---------------------------------------------------------------------------
# Verilog generation tests
# ---------------------------------------------------------------------------
def test_register_file_generates_verilog(params):
    rf = RegisterFile(params)
    vlog = VerilogEmitter().emit(rf)
    assert "module RegisterFile" in vlog
    assert len(vlog) > 1000


def test_alu_array_generates_verilog(params):
    alu = ALUArray(params)
    vlog = VerilogEmitter().emit(alu)
    assert "module ALUArray" in vlog
    assert len(vlog) > 1000


def test_tensor_core_generates_verilog(params):
    tc = TensorCore(params)
    vlog = VerilogEmitter().emit(tc)
    assert "module TensorCore" in vlog
    assert len(vlog) > 1000


def test_gpgpu_core_generates_verilog(params):
    core = GPGPUCore(params)
    emitter = VerilogEmitter()
    vlog = emitter.emit_design(core)
    assert "module GPGPUCore" in vlog
    assert len(vlog) > 50000  # large design


# ---------------------------------------------------------------------------
# Functional simulation tests
# ---------------------------------------------------------------------------
from rtlgen.sim import Simulator
from skills.gpgpu.core.alu_lane import ALULane


def test_alu_lane_add():
    """ALULane should compute ADD correctly."""
    alu = ALULane(data_width=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', isa.ALU_ADD)
    sim.poke('src_a', 10)
    sim.poke('src_b', 20)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 30


def test_alu_lane_mul():
    """ALULane should compute MUL correctly."""
    alu = ALULane(data_width=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', isa.ALU_MUL)
    sim.poke('src_a', 7)
    sim.poke('src_b', 6)
    sim.step()

    assert sim.peek('result') == 42


def test_alu_lane_compare():
    """ALULane should set predicate on compare."""
    alu = ALULane(data_width=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', isa.ALU_SETP_EQ)
    sim.poke('src_a', 42)
    sim.poke('src_b', 42)
    sim.step()

    assert sim.peek('pred_out') == 1

    sim.poke('op', isa.ALU_SETP_LT)
    sim.poke('src_a', 5)
    sim.poke('src_b', 10)
    sim.step()

    assert sim.peek('pred_out') == 1


def test_register_file_read_write(params):
    """RegisterFile should support 2R1W access."""
    rf = RegisterFile(params)
    sim = Simulator(rf)
    sim.reset('rst_n')

    # Write to lane 0, addr 5, data 0xDEADBEEF
    sim.poke('wr_en', 0b00000001)
    sim.poke('wr_addr', 5)
    sim.poke('wr_data_0', 0xDEADBEEF)
    sim.step()

    # Read from lane 0, addr 5
    sim.poke('rd_addr_a', 5)
    sim.step()
    assert sim.peek('rd_data_a_0') == 0xDEADBEEF


def test_warp_scheduler_launch_and_advance(params):
    """WarpScheduler should launch warps and advance PC."""
    ws = WarpScheduler(params)
    sim = Simulator(ws)
    sim.reset('rst_n')

    # Launch 2 warps at PC=0x100
    sim.poke('launch_valid', 1)
    sim.poke('launch_warps', 2)
    sim.poke('launch_pc', 0x100)
    sim.step()
    sim.poke('launch_valid', 0)

    # Before issue, PC should be launch_pc
    assert sim.peek('fetch_pc') == 0x100

    # Issue ready + fetch ready -> PC should advance
    sim.poke('issue_ready', 1)
    sim.poke('fetch_ready', 1)
    sim.step()
    assert sim.peek('issue_pc') == 0x101


def test_tensor_core_mma(params):
    """TensorCore should compute D = A @ B + C correctly."""
    tc = TensorCore(params)
    sim = Simulator(tc)
    sim.reset('rst_n')

    # Load A = identity (4x4)
    for i in range(16):
        sim.poke_memory('buf_a', i, 1 if i in [0, 5, 10, 15] else 0)
    # Load B = all ones
    for i in range(16):
        sim.poke_memory('buf_b', i, 1)
    # Load C = all zeros
    for i in range(16):
        sim.poke_memory('buf_c', i, 0)

    # Trigger start
    sim.poke('start', 1)
    sim.step()
    sim.poke('start', 0)
    sim.step()

    # D = I @ 1 + 0 = all ones
    assert sim.peek_memory('buf_d', 0) == 1
    assert sim.peek_memory('buf_d', 1) == 1
    assert sim.peek_memory('buf_d', 15) == 1


# ---------------------------------------------------------------------------
# Full-chip integration simulation test
# ---------------------------------------------------------------------------
def test_gpgpu_core_fullchip_add(params):
    """GPGPUCore should execute ADD and write back result end-to-end."""
    core = GPGPUCore(params)
    sim = Simulator(core)
    sim.reset('rst_n')
    sim.step()

    # Disable JIT for frontend to work around known AST/JIT sync issues
    for name, child, _ in sim._subsim_info:
        if name == 'frontend':
            child._jit = None

    # Build ADD r2 = r0 + r1 instruction
    instr_add = isa.encode_instr(
        opcode=isa.OP_ALU,
        func=isa.ALU_ADD,
        dst=2,
        src_a=0,
        src_b=1,
        unit=isa.UNIT_ALU,
    )
    instr_exit = isa.encode_instr(
        opcode=isa.OP_CTRL,
        func=isa.CTRL_EXIT,
        unit=isa.UNIT_ALU,
    )

    imem = {0: instr_add, 1: instr_exit}

    # Pre-load registers via regfile child simulator
    rf_sim = None
    for name, child, _ in sim._subsim_info:
        if name == 'regfile':
            rf_sim = child
            break
    assert rf_sim is not None

    for lane in range(params.warp_size):
        rf_sim.poke('wr_en', 1 << lane)
        rf_sim.poke('wr_addr', 0)
        rf_sim.poke(f'wr_data_{lane}', 10)
        rf_sim.step()
        rf_sim.poke('wr_addr', 1)
        rf_sim.poke(f'wr_data_{lane}', 20)
        rf_sim.step()
    rf_sim.poke('wr_en', 0)

    # Launch kernel
    sim.poke('launch_valid', 1)
    sim.poke('launch_warps', 1)
    sim.poke('launch_pc', 0)

    # Service any IMEM request
    if sim.peek('frontend_imem_req_valid'):
        addr = int(sim.peek('frontend_imem_req_addr'))
        sim.poke('frontend_imem_resp_valid', 1)
        sim.poke('frontend_imem_resp_data', imem.get(addr, 0))
    else:
        sim.poke('frontend_imem_resp_valid', 0)
        sim.poke('frontend_imem_resp_data', 0)

    sim.step()
    sim.poke('launch_valid', 0)

    # Run until kernel_done or max_cycles
    max_cycles = 20
    for cyc in range(max_cycles):
        if sim.peek('frontend_imem_req_valid'):
            addr = int(sim.peek('frontend_imem_req_addr'))
            sim.poke('frontend_imem_resp_valid', 1)
            sim.poke('frontend_imem_resp_data', imem.get(addr, 0))
        else:
            sim.poke('frontend_imem_resp_valid', 0)
            sim.poke('frontend_imem_resp_data', 0)
        sim.step()
        if sim.peek('kernel_done'):
            break

    assert sim.peek('kernel_done') == 1, "Kernel did not complete"

    # Verify r2 = 30 (10 + 20) for lane 0
    rf_sim.poke('rd_addr_a', 2)
    rf_sim.step()
    assert rf_sim.peek('rd_data_a_0') == 30


# ---------------------------------------------------------------------------
# Parameterized configuration tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cfg", [
    GPGPUParams(num_regs=64, reg_width=64, data_width=64),
    GPGPUParams(tensor_dim=8),
    GPGPUParams(icache_sets=32, l1_sets=32),
    GPGPUParams(scoreboard_entries=64, max_divergence_depth=16),
    GPGPUParams(shared_mem_size=32768, coalescer_width=256),
])
def test_gpgpu_core_parameterized(cfg):
    """GPGPUCore should instantiate with various parameter combinations."""
    core = GPGPUCore(cfg)
    assert core.name == "GPGPUCore"
    # Basic smoke: generate verilog
    vlog = VerilogEmitter().emit_design(core)
    assert "module GPGPUCore" in vlog
    assert len(vlog) > 10000
