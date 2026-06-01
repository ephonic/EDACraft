"""
L3 DSL — LSAddrGen, LSAddrGen.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LSAddrGen(Module):
    def __init__(self):
        super().__init__("lsaddrgen")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.op = Input(3, "op")
        self.base = Input(64, "base")
        self.offset = Input(64, "offset")
        self.addr = Output(64, "addr")
        self.is_load = Output(1, "is_load")
        self.is_store = Output(1, "is_store")
        self.valid = Output(1, "valid")
        self.width_code = Output(3, "width_code")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.addr <<= 0
                self.is_load <<= 0
                self.is_store <<= 0
                self.valid <<= 0
                self.width_code <<= 0
            with Else():
                self.addr <<= self.base + self.offset
                self.valid <<= self.enqueue
                self.is_load <<= (self.enqueue == 1) & (self.op < 4)
                self.is_store <<= (self.enqueue == 1) & (self.op >= 4)
                self.width_code <<= self.op & 3

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


