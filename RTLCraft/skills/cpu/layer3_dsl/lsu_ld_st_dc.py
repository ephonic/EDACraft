"""
L3 DSL — LSDataCheck, LSDataCheck.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LSDataCheck(Module):
    def __init__(self):
        super().__init__("lsdatacheck")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.addr = Input(4, "addr")
        self.op = Input(4, "op")
        self.is_store = Input(1, "is_store")
        self.byte_en = Output(8, "byte_en")
        self.misalign = Output(1, "misalign")
        self.is_signed = Output(1, "is_signed")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.byte_en <<= 0
                self.misalign <<= 0
                self.is_signed <<= 0
            with Elif((self.op == 0)):
                self.byte_en <<= 1 << self.addr[2:0]
                self.misalign <<= 0
                self.is_signed <<= 1
            with Elif((self.op == 1)):
                self.byte_en <<= 3 << self.addr[2:0]
                self.misalign <<= self.addr[0]
                self.is_signed <<= 1
            with Elif((self.op == 2)):
                self.byte_en <<= 15 << self.addr[2:0]
                self.misalign <<= self.addr[1] | self.addr[0]
                self.is_signed <<= 1
            with Elif((self.op == 3)):
                self.byte_en <<= 255
                self.misalign <<= self.addr[2] | self.addr[1] | self.addr[0]
                self.is_signed <<= 1
            with Elif((self.op == 4)):
                self.byte_en <<= 1 << self.addr[2:0]
                self.misalign <<= 0
                self.is_signed <<= 0
            with Elif((self.op == 5)):
                self.byte_en <<= 3 << self.addr[2:0]
                self.misalign <<= self.addr[0]
                self.is_signed <<= 0
            with Elif((self.op == 6)):
                self.byte_en <<= 15 << self.addr[2:0]
                self.misalign <<= self.addr[1] | self.addr[0]
                self.is_signed <<= 0
            with Else():
                self.byte_en <<= 0
                self.misalign <<= 0
                self.is_signed <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


