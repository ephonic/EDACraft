"""
NeuralAccel Instruction Decode Unit

Decodes 32-bit NPU instructions into control signals.

Instruction Format (Fence Counter v1):
  [31:28] opcode     (4-bit)
  [27:24] func       (4-bit sub-opcode)
  [23:18] rd         (6-bit destination buffer ID)
  [17:12] rs1        (6-bit source 1 buffer ID)
  [11:6]  rs2_imm    (6-bit source 2 ID or immediate)
  [5:3]   set_fence  (3-bit fence ID to set on dispatch)
  [2:0]   wait_fence (3-bit fence ID to wait before dispatch)

Supported Instructions:
  0x0 NOP        : no operation
  0x1 LOAD       : external memory -> SRAM
  0x2 STORE      : SRAM -> external memory
  0x3 GEMM       : launch systolic array
  0x4 VEC_ALU    : vector element-wise operation
  0x5 SFU        : special function unit
  0x6 CROSSBAR   : crossbar data movement
  0x7 SYNC       : synchronization barrier
  0x8 CONFIG     : configuration write
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Wire
from rtlgen.logic import If


# Opcodes
OP_NOP = 0x0
OP_LOAD = 0x1
OP_STORE = 0x2
OP_GEMM = 0x3
OP_VEC_ALU = 0x4
OP_SFU = 0x5
OP_CROSSBAR = 0x6
OP_SYNC = 0x7
OP_CONFIG = 0x8
OP_IM2COL = 0x9
OP_POOL = 0xA


class InstructionDecode(Module):
    """NPU instruction decoder."""

    def __init__(self, name: str = "InstructionDecode"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Raw instruction input
        self.instr_valid = Input(1, "instr_valid")
        self.instr_data = Input(32, "instr_data")

        # Decoded control outputs
        self.dec_valid = Output(1, "dec_valid")
        self.dec_opcode = Output(4, "dec_opcode")
        self.dec_func = Output(4, "dec_func")
        self.dec_rd = Output(6, "dec_rd")
        self.dec_rs1 = Output(6, "dec_rs1")
        self.dec_rs2_imm = Output(6, "dec_rs2_imm")
        self.dec_set_fence = Output(3, "dec_set_fence")
        self.dec_wait_fence = Output(3, "dec_wait_fence")

        # One-hot instruction type outputs
        self.is_nop = Output(1, "is_nop")
        self.is_load = Output(1, "is_load")
        self.is_store = Output(1, "is_store")
        self.is_gemm = Output(1, "is_gemm")
        self.is_vec_alu = Output(1, "is_vec_alu")
        self.is_sfu = Output(1, "is_sfu")
        self.is_crossbar = Output(1, "is_crossbar")
        self.is_sync = Output(1, "is_sync")
        self.is_config = Output(1, "is_config")
        self.is_im2col = Output(1, "is_im2col")
        self.is_pool = Output(1, "is_pool")

        # Field extraction wires
        self.opcode_wire = Wire(4, "opcode_wire")
        self.func_wire = Wire(4, "func_wire")
        self.rd_wire = Wire(6, "rd_wire")
        self.rs1_wire = Wire(6, "rs1_wire")
        self.rs2_imm_wire = Wire(6, "rs2_imm_wire")
        self.set_fence_wire = Wire(3, "set_fence_wire")
        self.wait_fence_wire = Wire(3, "wait_fence_wire")

        @self.comb
        def _extract():
            self.opcode_wire <<= self.instr_data[31:28]
            self.func_wire <<= self.instr_data[27:24]
            self.rd_wire <<= self.instr_data[23:18]
            self.rs1_wire <<= self.instr_data[17:12]
            self.rs2_imm_wire <<= self.instr_data[11:6]
            self.set_fence_wire <<= self.instr_data[5:3]
            self.wait_fence_wire <<= self.instr_data[2:0]

        @self.comb
        def _decode():
            self.dec_valid <<= self.instr_valid
            self.dec_opcode <<= self.opcode_wire
            self.dec_func <<= self.func_wire
            self.dec_rd <<= self.rd_wire
            self.dec_rs1 <<= self.rs1_wire
            self.dec_rs2_imm <<= self.rs2_imm_wire
            self.dec_set_fence <<= self.set_fence_wire
            self.dec_wait_fence <<= self.wait_fence_wire

            # One-hot decode (only valid when instr_valid is asserted)
            op = self.opcode_wire
            valid = self.instr_valid

            self.is_nop <<= valid & (op == OP_NOP)
            self.is_load <<= valid & (op == OP_LOAD)
            self.is_store <<= valid & (op == OP_STORE)
            self.is_gemm <<= valid & (op == OP_GEMM)
            self.is_vec_alu <<= valid & (op == OP_VEC_ALU)
            self.is_sfu <<= valid & (op == OP_SFU)
            self.is_crossbar <<= valid & (op == OP_CROSSBAR)
            self.is_sync <<= valid & (op == OP_SYNC)
            self.is_config <<= valid & (op == OP_CONFIG)
            self.is_im2col <<= valid & (op == OP_IM2COL)
            self.is_pool <<= valid & (op == OP_POOL)
