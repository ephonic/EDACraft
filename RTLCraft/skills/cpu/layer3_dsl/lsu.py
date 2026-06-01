"""
L3 DSL — LSU, LSU.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LSU(Module):
    def __init__(self):
        super().__init__("lsu")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.is_store = Input(1, "is_store")
        self.addr = Input(64, "addr")
        self.mem_rdata = Input(64, "mem_rdata")
        self.result = Output(64, "result")
        self.valid = Output(1, "valid")

        self.init = Reg(1, "init")
        self.s1_data = Reg(64, "s1_data")
        self.s1_v = Reg(1, "s1_v")
        self.s2_data = Reg(64, "s2_data")
        self.s2_v = Reg(1, "s2_v")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.result <<= 0
                self.valid <<= 0
            with Else():
                self.result <<= self.s2_data
                self.valid <<= self.s2_v

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.s1_v <<= 0
                self.s2_v <<= 0
            with Else():
                self.init <<= 1
                self.s1_v <<= (self.enqueue == 1) & (self.is_store == 0)
                with If((self.enqueue == 1)):
                    self.s1_data <<= self.mem_rdata
                self.s2_v <<= self.s1_v
                self.s2_data <<= self.s1_data


