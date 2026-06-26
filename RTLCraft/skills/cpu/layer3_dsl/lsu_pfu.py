"""
L3 DSL — PrefetchUnit, PrefetchUnit.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PrefetchUnit(Module):
    def __init__(self):
        super().__init__("prefetchunit")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.miss_addr = Input(64, "miss_addr")
        self.miss_valid = Input(1, "miss_valid")
        self.lfb_ready = Input(1, "lfb_ready")
        self.flush = Input(1, "flush")
        self.pf_addr = Output(64, "pf_addr")
        self.pf_valid = Output(1, "pf_valid")
        self.pf_active = Output(1, "pf_active")

        self.active = Reg(1, "active")
        self.addr_r = Reg(64, "addr_r")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pf_addr <<= 0
                self.pf_valid <<= 0
                self.pf_active <<= 0
            with Else():
                self.pf_active <<= self.active
                with If((self.active == 1) & (self.lfb_ready == 1)):
                    self.pf_addr <<= self.addr_r + 16
                    self.pf_valid <<= 1
                with Else():
                    self.pf_addr <<= 0
                    self.pf_valid <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.active <<= 0
                self.addr_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.active <<= 0
                with Elif((self.miss_valid == 1) & (self.lfb_ready == 1) & (self.active == 0)):
                    self.active <<= 1
                    self.addr_r <<= self.miss_addr
                with Elif((self.flush == 0)):
                    self.active <<= 0


