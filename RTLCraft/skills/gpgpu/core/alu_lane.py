"""
GPGPU ALU Lane —Single-thread arithmetic/logic unit

Supports integer and floating-point operations with 1-cycle latency.
Comparison operations output a predicate bit.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Mux

from skills.gpgpu.common import isa
from skills.gpgpu.common.params import GPGPUParams


class ALULane(Module):
    """Single-lane ALU for SIMT execution."""

    def __init__(self, data_width: int = 32, name: str = "ALULane"):
        super().__init__(name)
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control
        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.shift_amt = Input(5, "shift_amt")

        # Operands
        self.src_a = Input(data_width, "src_a")
        self.src_b = Input(data_width, "src_b")
        self.src_c = Input(data_width, "src_c")

        # Outputs
        self.out_valid = Output(1, "out_valid")
        self.result = Output(data_width, "result")
        self.pred_out = Output(1, "pred_out")

        # Internal result wires for each operation group
        self.int_result = Wire(data_width, "int_result")
        self.fp_result = Wire(data_width, "fp_result")
        self.cmp_result = Wire(1, "cmp_result")
        self.pred_result = Wire(1, "pred_result")
        self.mov_result = Wire(data_width, "mov_result")

        # Registered outputs
        self.result_r = Reg(data_width, "result_r")
        self.pred_r = Reg(1, "pred_r")
        self.valid_r = Reg(1, "valid_r")

        @self.comb
        def _compute():
            a = self.src_a
            b = self.src_b
            c = self.src_c
            op = self.op

            # Default results
            self.int_result <<= 0
            self.fp_result <<= 0
            self.cmp_result <<= 0
            self.pred_result <<= 0
            self.mov_result <<= 0

            # ---------------- Integer operations ----------------
            with If(op == isa.ALU_ADD):
                self.int_result <<= a + b
            with If(op == isa.ALU_SUB):
                self.int_result <<= a - b
            with If(op == isa.ALU_MUL):
                self.int_result <<= a * b
            with If(op == isa.ALU_MAD):
                self.int_result <<= (a * b) + c
            with If(op == isa.ALU_AND):
                self.int_result <<= a & b
            with If(op == isa.ALU_OR):
                self.int_result <<= a | b
            with If(op == isa.ALU_XOR):
                self.int_result <<= a ^ b
            with If(op == isa.ALU_NOT):
                self.int_result <<= ~a
            with If(op == isa.ALU_SHL):
                self.int_result <<= a << self.shift_amt
            with If(op == isa.ALU_SHR):
                self.int_result <<= a >> self.shift_amt
            with If(op == isa.ALU_ASR):
                self.int_result <<= a >> self.shift_amt  # Verilog >>> for arithmetic
            with If(op == isa.ALU_MIN):
                self.int_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_MAX):
                self.int_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_ABS):
                self.int_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_NEG):
                self.int_result <<= 0 - a

            # ---------------- FP operations (simple mapping) ----------------
            with If(op == isa.ALU_FADD):
                self.fp_result <<= a + b
            with If(op == isa.ALU_FSUB):
                self.fp_result <<= a - b
            with If(op == isa.ALU_FMUL):
                self.fp_result <<= a * b
            with If(op == isa.ALU_FMAD):
                self.fp_result <<= (a * b) + c
            with If(op == isa.ALU_FMIN):
                self.fp_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_FMAX):
                self.fp_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_FABS):
                self.fp_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_FNEG):
                self.fp_result <<= 0 - a

            # ---------------- Comparison (set predicate) ----------------
            with If(op == isa.ALU_SETP_EQ):
                self.cmp_result <<= (a == b)
            with If(op == isa.ALU_SETP_NE):
                self.cmp_result <<= (a != b)
            with If(op == isa.ALU_SETP_LT):
                self.cmp_result <<= (a < b)
            with If(op == isa.ALU_SETP_LE):
                self.cmp_result <<= (a <= b)
            with If(op == isa.ALU_SETP_GT):
                self.cmp_result <<= (a > b)
            with If(op == isa.ALU_SETP_GE):
                self.cmp_result <<= (a >= b)

            # ---------------- Move / Select ----------------
            with If(op == isa.MOV_MOV):
                self.mov_result <<= a
            with If(op == isa.MOV_SEL):
                self.mov_result <<= Mux(self.pred_out, a, b)

            # ---------------- Final mux: select result based on opcode range ----------------
            # Integer ops: 0b000xxx, FP ops: 0b010xxx, CMP: 0b100xxx, MOV: handled separately
            is_fp = (op >> 4) == 0b01
            is_cmp = (op >> 4) == 0b10

            self.result_r <<= Mux(is_cmp, 0, Mux(is_fp, self.fp_result, self.int_result))
            self.pred_r <<= Mux(is_cmp, self.cmp_result, 0)

        # Sequential: capture registered outputs
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _reg():
            self.valid_r <<= self.valid

        self.out_valid <<= self.valid_r
        self.result <<= self.result_r
        self.pred_out <<= self.pred_r
