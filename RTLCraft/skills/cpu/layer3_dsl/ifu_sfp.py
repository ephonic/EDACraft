"""
L3 DSL — SFP, SFP.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SFP(Module):
    def __init__(self):
        super().__init__("sfp")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.branch_taken = Input(1, "branch_taken")
        self.branch_mispredict = Input(1, "branch_mispredict")
        self.flush_external = Input(1, "flush_external")
        self.redirect = Input(1, "redirect")
        self.flush = Output(1, "flush")
        self.flush_redirect = Output(1, "flush_redirect")
        self.spec_depth = Output(4, "spec_depth")

        self.depth = Reg(4, "depth")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.flush <<= 0
                self.flush_redirect <<= 0
                self.spec_depth <<= 0
            with Else():
                self.flush <<= (self.branch_mispredict == 1) | (self.flush_external == 1)
                self.flush_redirect <<= self.redirect
                self.spec_depth <<= self.depth

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.depth <<= 0
            with Else():
                self.init <<= 1
                with If((self.branch_mispredict == 1)):
                    self.depth <<= 0
                with Elif((self.branch_taken == 1) & (self.depth < 7)):
                    self.depth <<= self.depth + 1
                with Elif((self.branch_taken == 0) & (self.depth > 0)):
                    self.depth <<= self.depth - 1
                with Else():
                    self.depth <<= self.depth


