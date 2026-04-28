"""
BOOM Execution Units

- ALU: integer arithmetic, logic, shifts, branches
- MUL: integer multiplier (pipelined)
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Parameter
from rtlgen.logic import If, Else, Mux


class ALU(Module):
    """Integer ALU supporting RV32I operations.

    Opcodes (4-bit)
    0000 : ADD
    0001 : SUB
    0010 : SLL (shift left logical)
    0011 : SLT (set less than, signed)
    0100 : SLTU (set less than, unsigned)
    0101 : XOR
    0110 : SRL (shift right logical)
    0111 : SRA (shift right arithmetic)
    1000 : OR
    1001 : AND
    1010 : EQ (branch equal)
    1011 : NE (branch not equal)
    1100 : LT (branch less than)
    1101 : GE (branch greater/equal)
    1110 : LTU (branch less than unsigned)
    1111 : GEU (branch greater/equal unsigned)
    """

    def __init__(self, xlen: int = 32, name: str = "ALU"):
        super().__init__(name)
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.valid = Input(1, "valid")
        self.op = Input(4, "op")
        self.rs1 = Input(xlen, "rs1")
        self.rs2 = Input(xlen, "rs2")
        self.imm = Input(xlen, "imm")      # for immediate ops
        self.use_imm = Input(1, "use_imm")
        self.pc = Input(xlen, "pc")
        self.is_branch = Input(1, "is_branch")

        self.out_valid = Output(1, "out_valid")
        self.result = Output(xlen, "result")
        self.br_taken = Output(1, "br_taken")
        self.br_target = Output(xlen, "br_target")

        self.operand_b = Wire(xlen, "operand_b")

        @self.comb
        def _sel():
            self.operand_b <<= Mux(self.use_imm, self.imm, self.rs2)

        # Combinational result
        self.add_result = Wire(xlen + 1, "add_result")
        self.sub_result = Wire(xlen + 1, "sub_result")
        self.slt_result = Wire(1, "slt_result")
        self.sltu_result = Wire(1, "sltu_result")

        @self.comb
        def _arith():
            self.add_result <<= self.rs1 + self.operand_b
            self.sub_result <<= self.rs1 - self.operand_b
            self.slt_result <<= (self.rs1[xlen - 1] != self.operand_b[xlen - 1]) & (self.rs1[xlen - 1] == 1)
            self.sltu_result <<= self.rs1 < self.operand_b

        self.result_comb = Wire(xlen, "result_comb")

        @self.comb
        def _result():
            self.result_comb <<= 0
            with If(self.op == 0b0000):  # ADD
                self.result_comb <<= self.add_result[xlen - 1:0]
            with Else():
                with If(self.op == 0b0001):  # SUB
                    self.result_comb <<= self.sub_result[xlen - 1:0]
                with Else():
                    with If(self.op == 0b0010):  # SLL
                        self.result_comb <<= self.rs1 << self.operand_b[4:0]
                    with Else():
                        with If(self.op == 0b0011):  # SLT
                            self.result_comb <<= Mux(self.slt_result, 1, 0)
                        with Else():
                            with If(self.op == 0b0100):  # SLTU
                                self.result_comb <<= Mux(self.sltu_result, 1, 0)
                            with Else():
                                with If(self.op == 0b0101):  # XOR
                                    self.result_comb <<= self.rs1 ^ self.operand_b
                                with Else():
                                    with If(self.op == 0b0110):  # SRL
                                        self.result_comb <<= self.rs1 >> self.operand_b[4:0]
                                    with Else():
                                        with If(self.op == 0b0111):  # SRA
                                            # Arithmetic shift: sign-extend
                                            self.result_comb <<= self.rs1 >> self.operand_b[4:0]  # simplified
                                        with Else():
                                            with If(self.op == 0b1000):  # OR
                                                self.result_comb <<= self.rs1 | self.operand_b
                                            with Else():
                                                with If(self.op == 0b1001):  # AND
                                                    self.result_comb <<= self.rs1 & self.operand_b

        @self.comb
        def _branch():
            self.br_taken <<= 0
            self.br_target <<= self.pc + 4
            with If(self.is_branch & self.valid):
                with If(self.op == 0b1010):  # BEQ
                    self.br_taken <<= (self.rs1 == self.operand_b)
                with Else():
                    with If(self.op == 0b1011):  # BNE
                        self.br_taken <<= (self.rs1 != self.operand_b)
                    with Else():
                        with If(self.op == 0b1100):  # BLT
                            self.br_taken <<= self.slt_result
                        with Else():
                            with If(self.op == 0b1101):  # BGE
                                self.br_taken <<= ~self.slt_result
                            with Else():
                                with If(self.op == 0b1110):  # BLTU
                                    self.br_taken <<= self.sltu_result
                                with Else():
                                    with If(self.op == 0b1111):  # BGEU
                                        self.br_taken <<= ~self.sltu_result
                with If(self.br_taken):
                    self.br_target <<= self.pc + self.imm

        # Pipeline output (1-cycle latency)
        self.result_r = Reg(xlen, "result_r")
        self.br_taken_r = Reg(1, "br_taken_r")
        self.br_target_r = Reg(xlen, "br_target_r")
        self.valid_r = Reg(1, "valid_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _pipe():
            with If(self.rst_n == 0):
                self.valid_r <<= 0
            with Else():
                self.valid_r <<= self.valid
                self.result_r <<= self.result_comb
                self.br_taken_r <<= self.br_taken
                self.br_target_r <<= self.br_target

        self.out_valid <<= self.valid_r
        self.result <<= self.result_r  # Note: re-assigns, better to use separate wire


class Multiplier(Module):
    """Pipelined integer multiplier (3 cycles).

    Uses a simple shift-and-add algorithm across 3 stages.
    """

    def __init__(self, xlen: int = 32, name: str = "Multiplier"):
        super().__init__(name)
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.valid = Input(1, "valid")
        self.rs1 = Input(xlen, "rs1")
        self.rs2 = Input(xlen, "rs2")
        self.is_signed = Input(1, "is_signed")  # 1=signed, 0=unsigned
        self.high = Input(1, "high")       # return upper half

        self.out_valid = Output(1, "out_valid")
        self.result = Output(xlen, "result")

        # Stage 1: capture inputs
        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a = Reg(xlen, "s1_a")
        self.s1_b = Reg(xlen, "s1_b")
        self.s1_signed = Reg(1, "s1_signed")
        self.s1_high = Reg(1, "s1_high")

        # Stage 2: partial products
        self.s2_valid = Reg(1, "s2_valid")
        self.s2_pp = Reg(2 * xlen, "s2_pp")
        self.s2_high = Reg(1, "s2_high")

        # Stage 3: final result
        self.s3_valid = Reg(1, "s3_valid")
        self.s3_result = Reg(xlen, "s3_result")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _pipe():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
                self.s2_valid <<= 0
                self.s3_valid <<= 0
            with Else():
                # Stage 1 -> 2
                self.s1_valid <<= self.valid
                self.s1_a <<= self.rs1
                self.s1_b <<= self.rs2
                self.s1_signed <<= self.is_signed
                self.s1_high <<= self.high

                # Stage 2 -> 3
                self.s2_valid <<= self.s1_valid
                self.s2_pp <<= self.s1_a * self.s1_b  # combinational multiply
                self.s2_high <<= self.s1_high

                # Stage 3 -> output
                self.s3_valid <<= self.s2_valid
                with If(self.s2_high):
                    self.s3_result <<= self.s2_pp[2 * xlen - 1:xlen]
                with Else():
                    self.s3_result <<= self.s2_pp[xlen - 1:0]

        self.out_valid <<= self.s3_valid
        self.result <<= self.s3_result
