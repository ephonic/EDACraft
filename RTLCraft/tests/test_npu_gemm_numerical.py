"""Numerical correctness test for SystolicArray GEMM via SystolicDataAdapter.

Directly writes matrices into SRAM banks via JIT memory, runs a GEMM
instruction, and reads back results to verify the data path.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from rtlgen.sim import Simulator

from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.frontend.instruction_decode import OP_GEMM


def _encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence=0, wait_fence=0):
    return ((opcode & 0xF) << 28) | ((func & 0xF) << 24) | ((rd & 0x3F) << 18) | ((rs1 & 0x3F) << 12) | ((rs2_imm & 0x3F) << 6) | ((set_fence & 0x7) << 3) | (wait_fence & 0x7)


def _write_jit_mem(sim, mem_name, data_dict):
    """Write data into a JIT-compiled memory region.
    
    Automatically masks values to the memory's bit width.
    """
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    for addr, val in data_dict.items():
        mem[addr] = int(val) & mask


def _read_jit_mem(sim, mem_name, addr, count=1):
    """Read data from a JIT-compiled memory region.
    
    Automatically masks values to the memory's bit width.
    """
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    if count == 1:
        return mem[addr] & mask
    return [mem[addr + i] & mask for i in range(count)]


def test_gemm_identity_2x2():
    """2×2 identity GEMM through the full data path."""
    array_size = 32
    k_dim = 2

    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    # -----------------------------------------------------------------
    # Load weight matrix (identity, 32×32) into SRAM_A bank0
    # Layout: addr = row * 32 + col
    # -----------------------------------------------------------------
    weights = {}
    for r in range(array_size):
        for c in range(array_size):
            weights[r * array_size + c] = 1 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, "sram_a_bank0", weights)

    # -----------------------------------------------------------------
    # Load activation matrix (identity, 32×32) into SRAM_B bank0
    # -----------------------------------------------------------------
    activations = {}
    for r in range(array_size):
        for c in range(array_size):
            activations[r * array_size + c] = 1 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, "sram_b_bank0", activations)

    # -----------------------------------------------------------------
    # Load a single GEMM instruction into instruction memory
    # -----------------------------------------------------------------
    gemm_instr = _encode_instr(OP_GEMM, func=0, rd=0, rs1=0, rs2_imm=k_dim)
    _write_jit_mem(sim, "inst_mem_mem", {0: gemm_instr})

    # -----------------------------------------------------------------
    # Run NPU
    # -----------------------------------------------------------------
    sim.poke("prog_length", 1)
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    max_cycles = 3000
    for i in range(max_cycles):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break

    assert completed, f"GEMM did not complete within {max_cycles} cycles (stopped at cycle {i})"

    # -----------------------------------------------------------------
    # Read results from SRAM_C bank0
    # -----------------------------------------------------------------
    result = _read_jit_mem(sim, "sram_c_bank0", 0, array_size * array_size)

    # Check key elements
    assert result[0] == 1, f"C[0,0] expected 1, got {result[0]}"
    assert result[1] == 0, f"C[0,1] expected 0, got {result[1]}"
    assert result[array_size + 1] == 1, f"C[1,1] expected 1, got {result[array_size + 1]}"
    assert result[array_size] == 0, f"C[1,0] expected 0, got {result[array_size]}"

    # Check a few more zeros
    assert result[2] == 0, f"C[0,2] expected 0, got {result[2]}"
    assert result[array_size + 2] == 0, f"C[1,2] expected 0, got {result[array_size + 2]}"


def test_gemm_scalar_mult():
    """Simple scalar scaling: weight = 3*I, act = 2*I → result = 6*I."""
    array_size = 32
    k_dim = 2

    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    weights = {}
    for r in range(array_size):
        for c in range(array_size):
            weights[r * array_size + c] = 3 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, "sram_a_bank0", weights)

    activations = {}
    for r in range(array_size):
        for c in range(array_size):
            activations[r * array_size + c] = 2 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, "sram_b_bank0", activations)

    gemm_instr = _encode_instr(OP_GEMM, func=0, rd=0, rs1=0, rs2_imm=k_dim)
    _write_jit_mem(sim, "inst_mem_mem", {0: gemm_instr})

    sim.poke("prog_length", 1)
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    for i in range(3000):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break

    assert completed, "GEMM did not complete"

    result = _read_jit_mem(sim, "sram_c_bank0", 0, array_size * array_size)
    # 3 * 2 = 6
    assert result[0] == 6, f"C[0,0] expected 6, got {result[0]}"
    assert result[array_size + 1] == 6, f"C[1,1] expected 6, got {result[array_size + 1]}"
    assert result[1] == 0, f"C[0,1] expected 0, got {result[1]}"
