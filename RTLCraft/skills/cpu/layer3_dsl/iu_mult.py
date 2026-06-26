"""
L3 DSL — Multiplier, Multiplier.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class Multiplier(Module):
    def __init__(self):
        super().__init__("multiplier")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.signed = Input(1, "signed")
        self.result = Output(64, "result")
        self.valid = Output(1, "valid")

        self.a_r = Reg(64, "a_r")
        self.b_r = Reg(64, "b_r")
        self.busy = Reg(1, "busy")
        self.cnt = Reg(7, "cnt")
        self.init = Reg(1, "init")
        self.neg = Reg(1, "neg")
        self.prod = Reg(128, "prod")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.valid <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.busy <<= 0
                self.cnt <<= 0
                self.a_r <<= 0
                self.b_r <<= 0
                self.prod <<= 0
                self.neg <<= 0
                self.result <<= 0
                self.valid <<= 0
            with Else():
                self.init <<= 1
                self.valid <<= 0
                with If((self.busy == 0)):
                    with If((self.enqueue == 1)):
                        self.busy <<= 1
                        self.cnt <<= 0
                        self.prod <<= 0
                        with If((self.signed == 1) & (self.a[63] == 1)):
                            self.a_r <<= ~self.a + 1
                        with Else():
                            self.a_r <<= self.a
                        with If((self.signed == 1) & (self.b[63] == 1)):
                            self.b_r <<= ~self.b + 1
                        with Else():
                            self.b_r <<= self.b
                        self.neg <<= (self.signed == 1) & (self.a[63] ^ self.b[63])
                with Else():
                    with If((self.b_r[0] == 1)):
                        self.prod <<= self.prod + self.a_r
                    self.a_r <<= self.a_r << 1
                    self.b_r <<= self.b_r >> 1
                    self.cnt <<= self.cnt + 1
                    with If((self.cnt == 63)):
                        self.busy <<= 0
                        with If((self.neg == 1)):
                            self.result <<= (((340282366920938463463374607431768211455 ^ self.prod) + 1) & 18446744073709551615)
                        with Else():
                            self.result <<= self.prod[63:0]
                        self.valid <<= 1


