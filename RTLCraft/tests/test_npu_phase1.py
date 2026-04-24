"""Phase 1 tests: NPU parameters and instruction decode."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.frontend.instruction_decode import (
    InstructionDecode,
    OP_NOP, OP_LOAD, OP_STORE, OP_GEMM, OP_VEC_ALU, OP_SFU, OP_CROSSBAR, OP_SYNC, OP_CONFIG,
)


# ---------------------------------------------------------------------------
# Parameter tests
# ---------------------------------------------------------------------------

def test_default_params():
    """Default params should have sensible values."""
    p = NeuralAccelParams()
    assert p.ARRAY_SIZE == 32
    assert p.DATA_WIDTH == 16
    assert p.ACC_WIDTH == 64
    assert p.SRAM_DEPTH == 8192
    assert p.NUM_LANES == 32
    assert p.ADDR_WIDTH == 13


def test_custom_params():
    """Custom params should compute derived values correctly."""
    p = NeuralAccelParams(array_size=16, sram_depth=1024)
    assert p.ARRAY_SIZE == 16
    assert p.ARRAY_SIZE_BITS == 4
    assert p.ADDR_WIDTH == 10


def test_verilog_params():
    """to_verilog_params should return Parameter objects."""
    p = NeuralAccelParams()
    vp = p.to_verilog_params()
    assert len(vp) == 5
    names = [param.name for param in vp]
    assert "ARRAY_SIZE" in names
    assert "DATA_WIDTH" in names


# ---------------------------------------------------------------------------
# Instruction Decode tests
# ---------------------------------------------------------------------------

def _encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence=0, wait_fence=0):
    """Helper to encode a 32-bit NPU instruction (Fence Counter v1)."""
    return ((opcode & 0xF) << 28) | ((func & 0xF) << 24) | ((rd & 0x3F) << 18) | ((rs1 & 0x3F) << 12) | ((rs2_imm & 0x3F) << 6) | ((set_fence & 0x7) << 3) | (wait_fence & 0x7)


def test_decode_nop():
    """Decoder should recognize NOP."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    instr = _encode_instr(OP_NOP, 0, 0, 0, 0)
    sim.poke('instr_valid', 1)
    sim.poke('instr_data', instr)
    sim.step()

    assert sim.peek('dec_valid') == 1
    assert sim.peek('dec_opcode') == OP_NOP
    assert sim.peek('is_nop') == 1
    assert sim.peek('is_load') == 0
    assert sim.peek('is_gemm') == 0


def test_decode_gemm():
    """Decoder should recognize GEMM with K dimension in immediate."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    # GEMM with K=32, buffer A=rs1=0, buffer C=rd=2
    instr = _encode_instr(OP_GEMM, 0x1, 2, 0, 32)
    sim.poke('instr_valid', 1)
    sim.poke('instr_data', instr)
    sim.step()

    assert sim.peek('dec_valid') == 1
    assert sim.peek('dec_opcode') == OP_GEMM
    assert sim.peek('dec_func') == 0x1
    assert sim.peek('dec_rd') == 2
    assert sim.peek('dec_rs1') == 0
    assert sim.peek('dec_rs2_imm') == 32
    assert sim.peek('is_gemm') == 1
    assert sim.peek('is_vec_alu') == 0


def test_decode_vec_alu():
    """Decoder should recognize VEC_ALU."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    # VEC_ALU ADD (func=0), src=buf0, dst=buf1
    instr = _encode_instr(OP_VEC_ALU, 0, 1, 0, 0)
    sim.poke('instr_valid', 1)
    sim.poke('instr_data', instr)
    sim.step()

    assert sim.peek('is_vec_alu') == 1
    assert sim.peek('dec_rd') == 1
    assert sim.peek('dec_rs1') == 0


def test_decode_crossbar():
    """Decoder should recognize CROSSBAR."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    # CROSSBAR block transfer (func=0)
    instr = _encode_instr(OP_CROSSBAR, 0, 3, 1, 16)
    sim.poke('instr_valid', 1)
    sim.poke('instr_data', instr)
    sim.step()

    assert sim.peek('is_crossbar') == 1
    assert sim.peek('dec_rd') == 3
    assert sim.peek('dec_rs1') == 1
    assert sim.peek('dec_rs2_imm') == 16


def test_decode_invalid():
    """Decoder should not assert any is_* when instr_valid is 0."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    sim.poke('instr_valid', 0)
    sim.poke('instr_data', _encode_instr(OP_GEMM, 0, 0, 0, 0))
    sim.step()

    assert sim.peek('dec_valid') == 0
    assert sim.peek('is_gemm') == 0
    assert sim.peek('is_nop') == 0


def test_decode_all_opcodes():
    """All opcodes should decode to correct is_* signals."""
    dec = InstructionDecode()
    sim = Simulator(dec)
    sim.reset('rst_n')

    tests = [
        (OP_NOP, 'is_nop'),
        (OP_LOAD, 'is_load'),
        (OP_STORE, 'is_store'),
        (OP_GEMM, 'is_gemm'),
        (OP_VEC_ALU, 'is_vec_alu'),
        (OP_SFU, 'is_sfu'),
        (OP_CROSSBAR, 'is_crossbar'),
        (OP_SYNC, 'is_sync'),
        (OP_CONFIG, 'is_config'),
    ]

    for opcode, signal_name in tests:
        sim.poke('instr_valid', 1)
        sim.poke('instr_data', _encode_instr(opcode, 0, 0, 0, 0))
        sim.step()

        assert sim.peek(signal_name) == 1, f"Opcode {opcode:#x} should set {signal_name}"
        # Ensure all others are 0
        for _, other_name in tests:
            if other_name != signal_name:
                assert sim.peek(other_name) == 0, f"{other_name} should be 0 for opcode {opcode:#x}"


def test_verilog_generation():
    """InstructionDecode should emit valid Verilog."""
    dec = InstructionDecode()
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(dec)
    assert "module InstructionDecode" in verilog
    assert "dec_opcode" in verilog
    assert "is_gemm" in verilog
