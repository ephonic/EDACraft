"""
L3 DSL — SnoopCtrl, SnoopCtrl.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SnoopCtrl(Module):
    def __init__(self):
        super().__init__("snoopctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.snoop_req = Input(1, "snoop_req")
        self.snoop_addr = Input(64, "snoop_addr")
        self.sq_addr = Input(64, "sq_addr")
        self.sq_hit = Input(1, "sq_hit")
        self.snoop_stall = Output(1, "snoop_stall")
        self.sq_invalidate = Output(1, "sq_invalidate")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.snoop_stall <<= 0
                self.sq_invalidate <<= 0
            with Else():
                self.snoop_stall <<= (self.snoop_req == 1) & (self.sq_hit == 1)
                self.sq_invalidate <<= (self.snoop_req == 1) & (self.sq_hit == 1)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


