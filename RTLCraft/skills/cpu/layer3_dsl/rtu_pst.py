"""
L3 DSL — PST, PST.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PST(Module):
    def __init__(self):
        super().__init__("pst")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.complete_pr = Input(7, "complete_pr")
        self.complete_en = Input(1, "complete_en")
        self.retire_pr = Input(7, "retire_pr")
        self.retire_en = Input(1, "retire_en")
        self.flush = Input(1, "flush")
        self.ready_bitmap = Output(64, "ready_bitmap")

        self.bitmap = Reg(64, "bitmap")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.ready_bitmap <<= 0
            with Else():
                self.ready_bitmap <<= self.bitmap

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.bitmap <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.bitmap <<= 0
                with Else():
                    with If((self.complete_en == 1)):
                        self.bitmap <<= self.bitmap | 1 << self.complete_pr
                    with If((self.retire_en == 1)):
                        self.bitmap <<= self.bitmap & ~(1 << self.retire_pr)


