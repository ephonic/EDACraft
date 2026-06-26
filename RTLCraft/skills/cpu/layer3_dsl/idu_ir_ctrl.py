"""
L3 DSL — IRCtrl, IRCtrl.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class IRCtrl(Module):
    def __init__(self):
        super().__init__("irctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.alloc_req = Input(1, "alloc_req")
        self.freelist_empty = Input(1, "freelist_empty")
        self.alloc_grant = Output(1, "alloc_grant")
        self.stall = Output(1, "stall")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.alloc_grant <<= 0
                self.stall <<= 0
            with Else():
                self.alloc_grant <<= (self.alloc_req == 1) & (self.freelist_empty == 0)
                self.stall <<= (self.alloc_req == 1) & (self.freelist_empty == 1)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


