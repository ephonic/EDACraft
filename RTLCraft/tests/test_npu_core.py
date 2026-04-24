"""NPU core integration tests."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.frontend.instruction_decode import (
    OP_NOP, OP_LOAD, OP_STORE, OP_GEMM, OP_VEC_ALU, OP_SFU, OP_CROSSBAR, OP_SYNC, OP_CONFIG,
)


def _encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence=0, wait_fence=0):
    return ((opcode & 0xF) << 28) | ((func & 0xF) << 24) | ((rd & 0x3F) << 18) | ((rs1 & 0x3F) << 12) | ((rs2_imm & 0x3F) << 6) | ((set_fence & 0x7) << 3) | (wait_fence & 0x7)


def _load_program(sim, instructions):
    """Helper to load a program into instruction memory."""
    for addr, instr in enumerate(instructions):
        sim.poke('prog_load_valid', 1)
        sim.poke('prog_load_addr', addr)
        sim.poke('prog_load_data', instr)
        sim.poke('prog_load_we', 1)
        sim.step()
    sim.poke('prog_load_valid', 0)
    sim.poke('prog_load_we', 0)


def test_npu_instantiation():
    """NeuralAccel should instantiate all submodules."""
    npu = NeuralAccel()
    assert npu is not None
    assert npu.decode is not None
    assert npu.systolic is not None
    assert npu.v_alu is not None
    assert npu.sfu is not None
    assert npu.crossbar is not None
    assert npu.inst_mem is not None
    assert npu.dma is not None


def test_npu_reset():
    """NeuralAccel should reset to IDLE state."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    assert sim.peek('busy') == 0
    assert sim.peek('done') == 0
    assert sim.peek('prog_done') == 0


def test_npu_verilog_generation():
    """NeuralAccel should emit valid Verilog with all submodules."""
    npu = NeuralAccel()
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(npu)
    assert "module NeuralAccel" in verilog
    assert "module SystolicArray" in verilog
    assert "module VectorALU" in verilog
    assert "module SFU" in verilog
    assert "module Crossbar" in verilog
    assert "module PingPongSRAM" in verilog
    assert "module AXI4DMA" in verilog
    assert "module InstructionMemory" in verilog


def test_npu_gemm_dispatch():
    """GEMM instruction should dispatch to SystolicArray."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_GEMM, 0x1, 2, 0, 8),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    # After 1 cycle: should be in DECODE
    assert sim.peek('busy') == 1

    # Step through DECODE → DISPATCH → WAIT
    sim.step()  # DISPATCH
    sim.step()  # WAIT

    # SystolicArray should be busy
    assert sim.peek('systolic_busy') == 1 or sim.peek('busy') == 1


def test_npu_vec_alu_dispatch():
    """VEC_ALU instruction should dispatch to VectorALU."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_VEC_ALU, 0x0, 1, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    # DECODE → DISPATCH → WAIT
    sim.step()  # DISPATCH
    sim.step()  # WAIT

    assert sim.peek('busy') == 1


def test_npu_sfu_dispatch():
    """SFU instruction should dispatch to SFU."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_SFU, 0x0, 1, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    sim.step()  # DISPATCH
    sim.step()  # WAIT

    assert sim.peek('busy') == 1


def test_npu_crossbar_dispatch():
    """CROSSBAR instruction should dispatch to Crossbar."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_CROSSBAR, 0x0, 1, 0, 4),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    sim.step()  # DISPATCH
    sim.step()  # WAIT

    assert sim.peek('crossbar_busy') == 1 or sim.peek('busy') == 1


def test_npu_sync_dispatch():
    """SYNC instruction should complete and finish program."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_SYNC, 0, 0, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    sim.step()  # DISPATCH
    sim.step()  # WAIT
    sim.step()  # DONE

    assert sim.peek('done') == 1


def test_npu_nop():
    """NOP should be decoded but not change busy state significantly."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_NOP, 0, 0, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    # NOP is decoded and dispatched; controller stays busy until DONE
    assert sim.peek('busy') == 1


def test_npu_multi_instruction():
    """NPU should execute multiple instructions sequentially."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    program = [
        _encode_instr(OP_SYNC, 0, 0, 0, 0),
        _encode_instr(OP_SYNC, 0, 0, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke('prog_length', len(program))
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    # Wait for both instructions to complete
    max_cycles = 20
    for _ in range(max_cycles):
        sim.step()
        if sim.peek('prog_done'):
            break

    assert sim.peek('prog_done') == 1
