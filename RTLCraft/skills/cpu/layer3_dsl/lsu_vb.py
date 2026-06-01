"""
L3 DSL — VictimBuffer, VictimBuffer.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class VictimBuffer(Module):
    def __init__(self):
        super().__init__("victimbuffer")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.victim_addr = Input(64, "victim_addr")
        self.victim_data = Input(128, "victim_data")
        self.victim_valid = Input(1, "victim_valid")
        self.wb_grant = Input(1, "wb_grant")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.wb_addr = Output(64, "wb_addr")
        self.wb_data = Output(128, "wb_data")
        self.wb_valid = Output(1, "wb_valid")
        self.empty = Output(1, "empty")

        self.cnt = Reg(3, "cnt")
        self.head = Reg(3, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(3, "tail")
        self.wb_a = Reg(64, "wb_a")
        self.wb_d = Reg(128, "wb_d")
        self.wb_v = Reg(1, "wb_v")

        self.vld = Array(1, 4, "vld")
        self.eaddr = Array(64, 4, "eaddr")
        self.edata = Array(128, 4, "edata")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.wb_addr <<= 0
                self.wb_data <<= 0
                self.wb_valid <<= 0
                self.empty <<= 1
            with Else():
                self.full <<= (self.cnt >= 4)
                self.empty <<= (self.cnt == 0)
                self.wb_addr <<= self.wb_a
                self.wb_data <<= self.wb_d
                self.wb_valid <<= self.wb_v

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.wb_v <<= 0
                self.vld[0] <<= 0
                self.vld[1] <<= 0
                self.vld[2] <<= 0
                self.vld[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.head <<= 0
                    self.tail <<= 0
                    self.cnt <<= 0
                    self.wb_v <<= 0
                    self.vld[0] <<= 0
                    self.vld[1] <<= 0
                    self.vld[2] <<= 0
                    self.vld[3] <<= 0
                with Else():
                    with If((self.wb_grant == 1) & (self.cnt > 0)):
                        self.wb_v <<= 1
                        self.wb_a <<= self.eaddr[self.head]
                        self.wb_d <<= self.edata[self.head]
                        self.vld[self.head] <<= 0
                        self.head <<= self.head + 1
                        self.cnt <<= self.cnt - 1
                    with Else():
                        self.wb_v <<= 0
                    with If((self.victim_valid == 1) & (self.cnt < 4)):
                        self.vld[self.tail] <<= 1
                        self.eaddr[self.tail] <<= self.victim_addr
                        self.edata[self.tail] <<= self.victim_data
                        self.tail <<= self.tail + 1
                        self.cnt <<= self.cnt + 1


