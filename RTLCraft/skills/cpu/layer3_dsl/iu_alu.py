"""
L3 DSL — iu_alu.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class iu_alu(Module):
    def __init__(self):
        super().__init__("iu_alu")

        self.clk = Input(1, "clk")
        self.opcode = Input(7, "opcode")
        self.rst_n = Input(1, "rst_n")
        self.src0 = Input(64, "src0")
        self.src1 = Input(64, "src1")
        self.result = Output(64, "result")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.result <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1
