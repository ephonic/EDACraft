"""
L3 DSL — StoreAddrGen, StoreAddrGen.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class StoreAddrGen(Module):
    def __init__(self):
        super().__init__("storeaddrgen")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.base = Input(64, "base")
        self.offset = Input(64, "offset")
        self.data = Input(64, "data")
        self.addr = Output(64, "addr")
        self.data_out = Output(64, "data_out")
        self.valid = Output(1, "valid")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.addr <<= 0
                self.data_out <<= 0
                self.valid <<= 0
            with Else():
                self.addr <<= self.base + self.offset
                self.data_out <<= self.data
                self.valid <<= self.enqueue

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


