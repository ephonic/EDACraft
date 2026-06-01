"""
L3 DSL — LoadDataArray, LoadDataArray.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LoadDataArray(Module):
    def __init__(self):
        super().__init__("loaddataarray")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rd_addr = Input(6, "rd_addr")
        self.way = Input(2, "way")
        self.req_valid = Input(1, "req_valid")
        self.rdata = Output(64, "rdata")
        self.rvalid = Output(1, "rvalid")

        self.init = Reg(1, "init")

        self.arr = Array(64, 256, "arr")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rdata <<= 0
                self.rvalid <<= 0
            with Else():
                self.rdata <<= self.arr[{self.way, self.rd_addr}]
                self.rvalid <<= self.req_valid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


