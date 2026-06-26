"""
L3 DSL — idu.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class idu(Module):
    def __init__(self):
        super().__init__("idu")

        self.clk = Input(1, "clk")
        self.fetch_valid = Input(1, "fetch_valid")
        self.rst_n = Input(1, "rst_n")
        self.decode_valid = Output(1, "decode_valid")
        self.iq_enqueue = Output(1, "iq_enqueue")
        self.rename_valid = Output(1, "rename_valid")
        self.Decode = Output(1, "Decode")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.decode_valid <<= 0
                self.iq_enqueue <<= 0
                self.rename_valid <<= 0
                self.Decode <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1
