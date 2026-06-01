"""
L3 DSL — Trap.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class Trap(Module):
    def __init__(self):
        super().__init__("trap")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.trap_valid = Input(1, "trap_valid")
        self.trap_cause = Input(64, "trap_cause")
        self.trap_pc = Input(64, "trap_pc")
        self.trap_ready = Output(1, "trap_ready")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If(self.init == 0): self.trap_ready <<= 0
            with Else(): self.trap_ready <<= 1

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0): self.init <<= 0
            with Else(): self.init <<= 1
