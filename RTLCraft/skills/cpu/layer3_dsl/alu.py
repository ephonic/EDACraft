"""
L3 DSL — ALU, ALU.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ALU(Module):
    def __init__(self):
        super().__init__("alu")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.op = Input(4, "op")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.result = Output(64, "result")
        self.zero = Output(1, "zero")

        self.shamt = Wire(7, "shamt")

        @self.comb
        def _comb():
            self.shamt <<= self.b[6:0]
            with If((self.op == 0)):
                self.result <<= self.a + self.b
            with Elif((self.op == 1)):
                self.result <<= self.a - self.b
            with Elif((self.op == 2)):
                self.result <<= self.a & self.b
            with Elif((self.op == 3)):
                self.result <<= self.a | self.b
            with Elif((self.op == 4)):
                self.result <<= self.a ^ self.b
            with Elif((self.op == 5)):
                self.result <<= self.a << self.shamt
            with Elif((self.op == 6)):
                self.result <<= self.a >> self.shamt
            with Elif((self.op == 7)):
                with If((self.a[63] == 0)):
                    self.result <<= self.a >> self.shamt
                with Else():
                    self.result <<= self.a >> self.shamt | 18446744073709551615 << 64 - self.shamt
            with Elif((self.op == 8)):
                with If(self.a[63] ^ self.b[63]):
                    self.result <<= self.a[63]
                with Else():
                    self.result <<= (self.a[62:0] < self.b[62:0])
            with Elif((self.op == 9)):
                self.result <<= (self.a < self.b)
            with Else():
                self.result <<= 0
            self.zero <<= (self.result == 0)


