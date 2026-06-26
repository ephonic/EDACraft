"""
L3 DSL — StoreDataExt, StoreDataExt.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class StoreDataExt(Module):
    def __init__(self):
        super().__init__("storedataext")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.data = Input(64, "data")
        self.addr_low = Input(4, "addr_low")
        self.op = Input(3, "op")
        self.aligned_data = Output(64, "aligned_data")
        self.byte_en = Output(8, "byte_en")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.aligned_data <<= 0
                self.byte_en <<= 0
            with Elif((self.op == 0)):
                self.aligned_data <<= (self.data & 255) << self.addr_low[2:0] * 8
                self.byte_en <<= 1 << self.addr_low[2:0]
            with Elif((self.op == 1)):
                self.aligned_data <<= (self.data & 65535) << self.addr_low[2:0] * 8
                self.byte_en <<= 3 << self.addr_low[2:0]
            with Elif((self.op == 2)):
                self.aligned_data <<= (self.data & 4294967295) << self.addr_low[2:0] * 8
                self.byte_en <<= 15 << self.addr_low[2:0]
            with Else():
                self.aligned_data <<= self.data
                self.byte_en <<= 255

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


