"""Standalone test: VEC_ALU ReLU on 8 elements via VPU."""

import sys
sys.path.insert(0, ".")

from rtlgen.sim import Simulator
from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.frontend.instruction_decode import (
    OP_NOP, OP_VEC_ALU, OP_SYNC,
)


def _encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence=0, wait_fence=0):
    return ((opcode & 0xF) << 28) | ((func & 0xF) << 24) | ((rd & 0x3F) << 18) | ((rs1 & 0x3F) << 12) | ((rs2_imm & 0x3F) << 6) | ((set_fence & 0x7) << 3) | (wait_fence & 0x7)


def _load_program(sim, instructions):
    for addr, instr in enumerate(instructions):
        sim.poke('prog_load_valid', 1)
        sim.poke('prog_load_addr', addr)
        sim.poke('prog_load_data', instr)
        sim.poke('prog_load_we', 1)
        sim.step()
    sim.poke('prog_load_valid', 0)
    sim.poke('prog_load_we', 0)


def _set_memory(sim, name, values):
    """Write values into a named memory (JIT-aware)."""
    if sim._jit is not None:
        idx = sim._jit.mem_idx[name]
        mem = sim._jit.memories[idx]
        for i, v in enumerate(values):
            mem[i] = int(v) & sim._jit.mem_masks[idx]
    else:
        mem = sim.memories[name]
        for i, v in enumerate(values):
            mem[i] = int(v) & ((1 << mem.width) - 1)


def _get_memory(sim, name, count):
    """Read values from a named memory (JIT-aware)."""
    if sim._jit is not None:
        idx = sim._jit.mem_idx[name]
        mem = sim._jit.memories[idx]
        return [int(mem[i]) for i in range(count)]
    else:
        mem = sim.memories[name]
        return [int(mem[i]) for i in range(count)]


def test_vpu_relu_8_elements():
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    # Program: ReLU on 8 elements in SRAM A
    # func=0x8 is ReLU, rd[1:0] selects buffer (0=SRAM_A), rs2_imm=8 elements
    program = [
        _encode_instr(OP_VEC_ALU, 0x8, 0, 0, 8),
        _encode_instr(OP_SYNC, 0, 0, 0, 0),
    ]
    _load_program(sim, program)

    # Pre-load 8 values into SRAM A bank0
    test_data = [0xFFF6, 0x0001, 0xFFFE, 0x0005, 0x8000, 0x0003, 0xFFFF, 0x000A]
    expected  = [0x0000, 0x0001, 0x0000, 0x0005, 0x0000, 0x0003, 0x0000, 0x000A]
    _set_memory(sim, 'sram_a_bank0', test_data)

    # Run program
    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    # Step until done (max 200 cycles) with debug
    for c in range(200):
        sim.step()
        state = sim.peek('state')
        vpu_state = sim.peek('vpu_state')
        vec_alu_busy = sim.peek('vec_alu_busy')
        busy = sim.peek('busy')
        done = sim.peek('done')
        if c < 30 or done == 1:
            print(f"cycle {c:3d}: state={state}, vpu_state={vpu_state}, vec_alu_busy={vec_alu_busy}, busy={busy}, done={done}")
        if done == 1:
            break

    assert sim.peek('done') == 1, "Program did not finish in time"
    assert sim.peek('busy') == 0, "NPU still busy after done"

    # Read back results from SRAM A bank0
    results = _get_memory(sim, 'sram_a_bank0', 8)

    print("Input:   ", [f"{v & 0xFFFF:04x}" for v in test_data])
    print("Expected:", [f"{v & 0xFFFF:04x}" for v in expected])
    print("Got:     ", [f"{v & 0xFFFF:04x}" for v in results])

    for i in range(8):
        assert (results[i] & 0xFFFF) == (expected[i] & 0xFFFF), \
            f"Mismatch at index {i}: expected {expected[i]:04x}, got {results[i]:04x}"

    print("VPU ReLU 8-element test PASSED")


if __name__ == "__main__":
    test_vpu_relu_8_elements()
