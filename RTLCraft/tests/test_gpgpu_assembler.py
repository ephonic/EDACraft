"""
Tests for the GPGPU assembler.
"""

import sys
sys.path.insert(0, "g:/code/rtlgen")

from skills.gpgpu.assembler import assemble
from skills.gpgpu.common import isa


def test_assemble_add():
    code = """
        ADD r1, r2, r3
    """
    mc = assemble(code)
    assert len(mc) == 1
    d = isa.decode_instr(mc[0])
    assert d["opcode"] == isa.OP_ALU
    assert d["func"] == isa.ALU_ADD
    assert d["dst"] == 1
    assert d["src_a"] == 2
    assert d["src_b"] == 3
    assert d["unit"] == isa.UNIT_ALU


def test_assemble_add_imm():
    code = """
        ADD r5, r6, #42
    """
    mc = assemble(code)
    d = isa.decode_instr(mc[0])
    assert d["dst"] == 5
    assert d["src_a"] == 6
    assert d["imm"] == 42


def test_assemble_branch_label():
    code = """
        BRA loop
        ADD r1, r2, r3
    loop:
        EXIT
    """
    mc = assemble(code)
    assert len(mc) == 3
    # BRA should encode imm = address of loop = 2
    d = isa.decode_instr(mc[0])
    assert d["opcode"] == isa.OP_CTRL
    assert d["func"] == isa.CTRL_BRA
    assert d["imm"] == 2


def test_assemble_memory():
    code = """
        LD r1, [r2]
        LD r3, [r4, #16]
        ST [r5], r6
        ST [r7, #4], r8
    """
    mc = assemble(code)
    assert len(mc) == 4

    d0 = isa.decode_instr(mc[0])
    assert d0["opcode"] == isa.OP_MEM
    assert d0["func"] == isa.MEM_LD
    assert d0["dst"] == 1
    assert d0["src_a"] == 2

    d1 = isa.decode_instr(mc[1])
    assert d1["dst"] == 3
    assert d1["src_a"] == 4
    assert d1["imm"] == 16

    d2 = isa.decode_instr(mc[2])
    assert d2["func"] == isa.MEM_ST
    assert d2["src_a"] == 5
    assert d2["src_b"] == 6

    d3 = isa.decode_instr(mc[3])
    assert d3["src_a"] == 7
    assert d3["imm"] == 4
    assert d3["src_b"] == 8


def test_assemble_control():
    code = """
        SYNC
        EXIT
        NOP
    """
    mc = assemble(code)
    assert len(mc) == 3

    d0 = isa.decode_instr(mc[0])
    assert d0["opcode"] == isa.OP_CTRL
    assert d0["func"] == isa.CTRL_SYNC

    d1 = isa.decode_instr(mc[1])
    assert d1["func"] == isa.CTRL_EXIT

    d2 = isa.decode_instr(mc[2])
    assert d2["func"] == isa.CTRL_NOP


def test_assemble_compare():
    code = """
        SETP.EQ r1, r2, r3
    """
    mc = assemble(code)
    d = isa.decode_instr(mc[0])
    assert d["opcode"] == isa.OP_ALU
    assert d["func"] == isa.ALU_SETP_EQ


def test_assemble_sfu():
    code = """
        RECIP r1, r2
    """
    mc = assemble(code)
    d = isa.decode_instr(mc[0])
    assert d["opcode"] == isa.OP_SFU
    assert d["func"] == isa.SFU_RECIP
    assert d["unit"] == isa.UNIT_SFU


def test_assemble_mov_sel():
    code = """
        MOV r1, r2
        SEL r3, r4, r5, p0
    """
    mc = assemble(code)
    d0 = isa.decode_instr(mc[0])
    assert d0["opcode"] == isa.OP_MOV
    assert d0["func"] == isa.MOV_MOV
    assert d0["dst"] == 1
    assert d0["src_a"] == 2

    d1 = isa.decode_instr(mc[1])
    assert d1["opcode"] == isa.OP_MOV
    assert d1["func"] == isa.MOV_SEL
    assert d1["dst"] == 3
    assert d1["src_a"] == 4
    assert d1["src_b"] == 5
    assert d1["pred_use"] == 1
    assert d1["pred_reg"] == 0
