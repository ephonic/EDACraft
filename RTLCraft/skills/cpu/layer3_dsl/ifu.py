"""
L3 DSL — ifu.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ifu(Module):
    def __init__(self):
        super().__init__("ifu")

        self.clk = Input(1, "clk")
        self.icache_rdata = Input(64, "icache_rdata")
        self.icache_valid = Input(1, "icache_valid")
        self.rst_n = Input(1, "rst_n")
        self.fetch_instr = Output(32, "fetch_instr")
        self.fetch_valid = Output(1, "fetch_valid")
        self.icache_addr = Output(64, "icache_addr")
        self.icache_req = Output(1, "icache_req")
        self.Fetch = Output(1, "Fetch")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.fetch_instr <<= 0
                self.fetch_valid <<= 0
                self.icache_addr <<= 0
                self.icache_req <<= 0
                self.Fetch <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1
