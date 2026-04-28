"""
NeuralAccel Vector ALU

8-lane SIMD ALU for element-wise operations.
Each lane operates independently on 16-bit data.

Supported operations (4-bit func):
  0000 : ADD
  0001 : SUB
  0010 : MUL
  0011 : MAX
  0100 : MIN
  0101 : AND
  0110 : OR
  0111 : XOR
  1000 : ReLU  (max(0, x))
  1001 : NOT   (bitwise invert)
  1010 : LSHIFT (left shift by rs2_imm[3:0])
  1011 : RSHIFT (logical right shift by rs2_imm[3:0])

1-cycle latency with valid/ready handshake.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


VEC_ADD = 0b0000
VEC_SUB = 0b0001
VEC_MUL = 0b0010
VEC_MAX = 0b0011
VEC_MIN = 0b0100
VEC_AND = 0b0101
VEC_OR = 0b0110
VEC_XOR = 0b0111
VEC_RELU = 0b1000
VEC_NOT = 0b1001
VEC_LSHIFT = 0b1010
VEC_RSHIFT = 0b1011


class VectorALU(Module):
    """8-lane SIMD vector ALU."""

    def __init__(self, num_lanes: int = 8, data_width: int = 16, name: str = "VectorALU"):
        super().__init__(name)
        self.num_lanes = num_lanes
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Input operands
        self.valid = Input(1, "valid")
        self.op = Input(4, "op")
        self.shift_amt = Input(4, "shift_amt")  # for LSHIFT/RSHIFT

        self.a = Vector(data_width, num_lanes, "a", vtype=Input)
        self.b = Vector(data_width, num_lanes, "b", vtype=Input)

        # Output
        self.out_valid = Output(1, "out_valid")
        self.result = Vector(data_width, num_lanes, "result", vtype=Output)

        # Per-lane combinational result
        self.lane_result = [Wire(data_width, f"lane_result_{i}") for i in range(num_lanes)]

        @self.comb
        def _compute():
            for i in range(num_lanes):
                a = self.a[i]
                b = self.b[i]
                res = self.lane_result[i]

                res <<= 0
                with If(self.op == VEC_ADD):
                    res <<= a + b
                with If(self.op == VEC_SUB):
                    res <<= a - b
                with If(self.op == VEC_MUL):
                    res <<= a * b
                with If(self.op == VEC_MAX):
                    res <<= Mux(a > b, a, b)
                with If(self.op == VEC_MIN):
                    res <<= Mux(a < b, a, b)
                with If(self.op == VEC_AND):
                    res <<= a & b
                with If(self.op == VEC_OR):
                    res <<= a | b
                with If(self.op == VEC_XOR):
                    res <<= a ^ b
                with If(self.op == VEC_RELU):
                    # ReLU: max(0, a) — check sign bit
                    res <<= Mux(a[self.data_width - 1] == 1, 0, a)
                with If(self.op == VEC_NOT):
                    res <<= ~a
                with If(self.op == VEC_LSHIFT):
                    res <<= a << self.shift_amt
                with If(self.op == VEC_RSHIFT):
                    res <<= a >> self.shift_amt

        # Pipeline output (1-cycle latency)
        self.valid_r = Reg(1, "valid_r")
        self.result_r = [Reg(data_width, f"result_r_{i}") for i in range(num_lanes)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _pipe():
            with If(self.rst_n == 0):
                self.valid_r <<= 0
                for i in range(num_lanes):
                    self.result_r[i] <<= 0
            with Else():
                self.valid_r <<= self.valid
                for i in range(num_lanes):
                    self.result_r[i] <<= self.lane_result[i]

        self.out_valid <<= self.valid_r
        for i in range(num_lanes):
            self.result[i] <<= self.result_r[i]
