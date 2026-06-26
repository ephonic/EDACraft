"""
L3 DSL — Divider, Divider.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class Divider(Module):
    def __init__(self):
        super().__init__("divider")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.signed = Input(1, "signed")
        self.quot = Output(64, "quot")
        self.rem = Output(64, "rem")
        self.valid = Output(1, "valid")
        self.busy = Output(1, "busy")

        self.b_abs = Reg(64, "b_abs")
        self.busy_r = Reg(1, "busy_r")
        self.cnt = Reg(7, "cnt")
        self.init = Reg(1, "init")
        self.neg_quot = Reg(1, "neg_quot")
        self.neg_rem = Reg(1, "neg_rem")
        self.quot_r = Reg(64, "quot_r")
        self.rem_r = Reg(64, "rem_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.busy <<= 0
                self.valid <<= 0
            with Else():
                self.busy <<= self.busy_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.busy_r <<= 0
                self.cnt <<= 0
                self.b_abs <<= 0
                self.rem_r <<= 0
                self.quot_r <<= 0
                self.neg_quot <<= 0
                self.neg_rem <<= 0
                self.quot <<= 0
                self.rem <<= 0
                self.valid <<= 0
            with Else():
                self.init <<= 1
                self.valid <<= 0
                with If((self.busy_r == 0)):
                    with If((self.enqueue == 1)):
                        self.busy_r <<= 1
                        self.cnt <<= 0
                        self.rem_r <<= 0
                        with If((self.signed == 1) & (self.a[63] == 1)):
                            self.quot_r <<= ~self.a + 1
                        with Else():
                            self.quot_r <<= self.a
                        with If((self.signed == 1) & (self.b[63] == 1)):
                            self.b_abs <<= ~self.b + 1
                        with Else():
                            self.b_abs <<= self.b
                        self.neg_quot <<= (self.signed == 1) & (self.a[63] ^ self.b[63])
                        self.neg_rem <<= (self.signed == 1) & (self.a[63] == 1)
                with Elif((self.cnt == 63)):
                    self.busy_r <<= 0
                    with If(self.b_abs <= (self.rem_r << 1 | self.quot_r[63] & 1)):
                        self.quot <<= self.quot_r << 1 | 1
                        self.rem <<= (self.rem_r << 1 | self.quot_r[63] & 1) - self.b_abs
                    with Else():
                        self.quot <<= self.quot_r << 1
                        self.rem <<= self.rem_r << 1 | self.quot_r[63] & 1
                    self.valid <<= 1
                with Else():
                    with If(self.b_abs <= (self.rem_r << 1 | self.quot_r[63] & 1)):
                        self.rem_r <<= (self.rem_r << 1 | self.quot_r[63] & 1) - self.b_abs
                        self.quot_r <<= self.quot_r << 1 | 1
                    with Else():
                        self.rem_r <<= self.rem_r << 1 | self.quot_r[63] & 1
                        self.quot_r <<= self.quot_r << 1
                    self.cnt <<= self.cnt + 1


