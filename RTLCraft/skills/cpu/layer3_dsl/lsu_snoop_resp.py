"""
L3 DSL — SnoopResp, SnoopResp.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SnoopResp(Module):
    def __init__(self):
        super().__init__("snoopresp")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.snoop_addr = Input(64, "snoop_addr")
        self.cache_hit = Input(1, "cache_hit")
        self.cache_shared = Input(1, "cache_shared")
        self.cache_dirty = Input(1, "cache_dirty")
        self.req_valid = Input(1, "req_valid")
        self.resp = Output(2, "resp")
        self.resp_valid = Output(1, "resp_valid")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.resp <<= 0
                self.resp_valid <<= 0
            with Else():
                self.resp_valid <<= self.req_valid
                with If((self.cache_hit == 0)):
                    self.resp <<= 0
                with Elif((self.cache_dirty == 1)):
                    self.resp <<= 2
                with Elif((self.cache_shared == 1)):
                    self.resp <<= 3
                with Else():
                    self.resp <<= 1

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


