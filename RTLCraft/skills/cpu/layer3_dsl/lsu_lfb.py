"""
L3 DSL — LFB, LFB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LFB(Module):
    def __init__(self):
        super().__init__("lfb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.alloc = Input(1, "alloc")
        self.miss_addr = Input(64, "miss_addr")
        self.fill_done = Input(1, "fill_done")
        self.fill_addr = Input(64, "fill_addr")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.pending = Output(1, "pending")
        self.match = Output(1, "match")
        self.match_addr = Output(64, "match_addr")

        self.cnt = Reg(3, "cnt")
        self.init = Reg(1, "init")

        self.vld = Array(1, 4, "vld")
        self.eaddr = Array(64, 4, "eaddr")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.pending <<= 0
                self.match <<= 0
                self.match_addr <<= 0
            with Else():
                self.full <<= (self.cnt >= 4)
                self.pending <<= (self.cnt > 0)
                self.match <<= (self.vld[0] == 1) & (self.eaddr[0] == self.miss_addr) | (self.vld[1] == 1) & (self.eaddr[1] == self.miss_addr) | (self.vld[2] == 1) & (self.eaddr[2] == self.miss_addr) | (self.vld[3] == 1) & (self.eaddr[3] == self.miss_addr)
                with If(((self.vld[0] == 1) & (self.eaddr[0] == self.miss_addr)) == 1):
                    self.match_addr <<= self.eaddr[0]
                with Elif(((self.vld[1] == 1) & (self.eaddr[1] == self.miss_addr)) == 1):
                    self.match_addr <<= self.eaddr[1]
                with Elif(((self.vld[2] == 1) & (self.eaddr[2] == self.miss_addr)) == 1):
                    self.match_addr <<= self.eaddr[2]
                with Elif(((self.vld[3] == 1) & (self.eaddr[3] == self.miss_addr)) == 1):
                    self.match_addr <<= self.eaddr[3]
                with Else():
                    self.match_addr <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.cnt <<= 0
                self.vld[0] <<= 0
                self.vld[1] <<= 0
                self.vld[2] <<= 0
                self.vld[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.cnt <<= 0
                    self.vld[0] <<= 0
                    self.vld[1] <<= 0
                    self.vld[2] <<= 0
                    self.vld[3] <<= 0
                with Else():
                    with If((self.fill_done == 1) & (self.cnt > 0)):
                        with If(((self.vld[0] == 1) & (self.eaddr[0] == self.fill_addr)) == 1):
                            self.vld[0] <<= 0
                            self.cnt <<= self.cnt - 1
                        with Elif(((self.vld[1] == 1) & (self.eaddr[1] == self.fill_addr)) == 1):
                            self.vld[1] <<= 0
                            self.cnt <<= self.cnt - 1
                        with Elif(((self.vld[2] == 1) & (self.eaddr[2] == self.fill_addr)) == 1):
                            self.vld[2] <<= 0
                            self.cnt <<= self.cnt - 1
                        with Elif(((self.vld[3] == 1) & (self.eaddr[3] == self.fill_addr)) == 1):
                            self.vld[3] <<= 0
                            self.cnt <<= self.cnt - 1
                    with If((self.alloc == 1) & (self.cnt < 4)):
                        with If((self.vld[0] == 0)):
                            self.vld[0] <<= 1
                            self.eaddr[0] <<= self.miss_addr
                            self.cnt <<= self.cnt + 1
                        with Elif((self.vld[1] == 0)):
                            self.vld[1] <<= 1
                            self.eaddr[1] <<= self.miss_addr
                            self.cnt <<= self.cnt + 1
                        with Elif((self.vld[2] == 0)):
                            self.vld[2] <<= 1
                            self.eaddr[2] <<= self.miss_addr
                            self.cnt <<= self.cnt + 1
                        with Elif((self.vld[3] == 0)):
                            self.vld[3] <<= 1
                            self.eaddr[3] <<= self.miss_addr
                            self.cnt <<= self.cnt + 1


