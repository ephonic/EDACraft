"""
L3 DSL — LoadAddrGen, LoadAddrGen.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LoadAddrGen(Module):
    def __init__(self):
        super().__init__("loadaddrgen")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.base = Input(64, "base")
        self.offset = Input(64, "offset")
        self.addr = Output(64, "addr")
        self.valid = Output(1, "valid")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.addr <<= 0
                self.valid <<= 0
            with Else():
                self.addr <<= self.base + self.offset
                self.valid <<= self.enqueue

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


