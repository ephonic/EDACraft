"""
L3 DSL — FwdNet, FwdNet.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class FwdNet(Module):
    def __init__(self):
        super().__init__("fwdnet")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rd_addr1 = Input(6, "rd_addr1")
        self.rd_addr2 = Input(6, "rd_addr2")
        self.rd_data1_raw = Input(64, "rd_data1_raw")
        self.rd_data2_raw = Input(64, "rd_data2_raw")
        self.fwd0_addr = Input(6, "fwd0_addr")
        self.fwd0_data = Input(64, "fwd0_data")
        self.fwd0_en = Input(1, "fwd0_en")
        self.fwd1_addr = Input(6, "fwd1_addr")
        self.fwd1_data = Input(64, "fwd1_data")
        self.fwd1_en = Input(1, "fwd1_en")
        self.rd_data1 = Output(64, "rd_data1")
        self.rd_data2 = Output(64, "rd_data2")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rd_data1 <<= 0
                self.rd_data2 <<= 0
            with Else():
                with If((self.rd_addr1 == 0)):
                    self.rd_data1 <<= 0
                with Elif((self.fwd0_en == 1) & (self.fwd0_addr == self.rd_addr1)):
                    self.rd_data1 <<= self.fwd0_data
                with Elif((self.fwd1_en == 1) & (self.fwd1_addr == self.rd_addr1)):
                    self.rd_data1 <<= self.fwd1_data
                with Else():
                    self.rd_data1 <<= self.rd_data1_raw
                with If((self.rd_addr2 == 0)):
                    self.rd_data2 <<= 0
                with Elif((self.fwd0_en == 1) & (self.fwd0_addr == self.rd_addr2)):
                    self.rd_data2 <<= self.fwd0_data
                with Elif((self.fwd1_en == 1) & (self.fwd1_addr == self.rd_addr2)):
                    self.rd_data2 <<= self.fwd1_data
                with Else():
                    self.rd_data2 <<= self.rd_data2_raw

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


