"""
L3 DSL — SpecFailPredict, SpecFailPredict.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SpecFailPredict(Module):
    def __init__(self):
        super().__init__("specfailpredict")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ld_addr = Input(64, "ld_addr")
        self.st_addr0 = Input(64, "st_addr0")
        self.st_addr1 = Input(64, "st_addr1")
        self.st_addr2 = Input(64, "st_addr2")
        self.st_addr3 = Input(64, "st_addr3")
        self.st_vld0 = Input(1, "st_vld0")
        self.st_vld1 = Input(1, "st_vld1")
        self.st_vld2 = Input(1, "st_vld2")
        self.st_vld3 = Input(1, "st_vld3")
        self.flush = Input(1, "flush")
        self.predict_fail = Output(1, "predict_fail")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.predict_fail <<= 0
            with Else():
                self.predict_fail <<= (self.st_vld0 == 1) & (self.st_addr0 == self.ld_addr) | (self.st_vld1 == 1) & (self.st_addr1 == self.ld_addr) | (self.st_vld2 == 1) & (self.st_addr2 == self.ld_addr) | (self.st_vld3 == 1) & (self.st_addr3 == self.ld_addr)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


