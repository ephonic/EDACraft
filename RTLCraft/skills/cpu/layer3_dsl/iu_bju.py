"""
L3 DSL — BJU, BJU.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class BJU(Module):
    def __init__(self):
        super().__init__("bju")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.op = Input(3, "op")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.pc = Input(64, "pc")
        self.taken = Output(1, "taken")
        self.target = Output(64, "target")

        @self.comb
        def _comb():
            with If((self.op == 0)):
                self.target <<= self.pc + self.b
                self.taken <<= (self.a == self.b)
            with Elif((self.op == 1)):
                self.target <<= self.pc + self.b
                self.taken <<= (self.a != self.b)
            with Elif((self.op == 2)):
                self.target <<= self.pc + self.b
                self.taken <<= 1
            with Elif((self.op == 3)):
                self.target <<= self.a + self.b & 18446744073709551614
                self.taken <<= 1
            with Elif((self.op == 4)):
                self.target <<= self.pc + self.b
                with If(self.a[63] ^ self.b[63]):
                    self.taken <<= self.a[63]
                with Else():
                    self.taken <<= (self.a[62:0] < self.b[62:0])
            with Elif((self.op == 5)):
                self.target <<= self.pc + self.b
                with If(self.a[63] ^ self.b[63]):
                    self.taken <<= (self.a[63] == 0)
                with Else():
                    self.taken <<= (self.a[62:0] >= self.b[62:0])
            with Elif((self.op == 6)):
                self.target <<= self.pc + self.b
                self.taken <<= (self.a < self.b)
            with Elif((self.op == 7)):
                self.target <<= self.pc + self.b
                self.taken <<= (self.a >= self.b)
            with Else():
                self.target <<= 0
                self.taken <<= 0


