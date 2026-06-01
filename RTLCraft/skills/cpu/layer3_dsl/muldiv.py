"""
L3 DSL — MulDiv, MulDiv.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class MulDiv(Module):
    def __init__(self):
        super().__init__("muldiv")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.op = Input(2, "op")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.result = Output(64, "result")
        self.valid = Output(1, "valid")

        self.acc = Reg(128, "acc")
        self.busy = Reg(1, "busy")
        self.cycle = Reg(6, "cycle")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.result <<= 0
                self.valid <<= 0
            with Else():
                self.result <<= self.acc[127:64]
                self.valid <<= (self.busy == 0) & (self.cycle > 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.busy <<= 0
                self.cycle <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1) & (self.busy == 0)):
                    self.busy <<= 1
                    self.cycle <<= 0
                    self.acc <<= self.a * self.b
                with If((self.busy == 1)):
                    self.cycle <<= self.cycle + 1
                    with If((self.cycle >= 2)):
                        self.busy <<= 0


