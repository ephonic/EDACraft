"""
L3 DSL — SnoopSNQ, SnoopSNQ.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SnoopSNQ(Module):
    def __init__(self):
        super().__init__("snoopsnq")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.push = Input(1, "push")
        self.snoop_addr = Input(64, "snoop_addr")
        self.snoop_id = Input(4, "snoop_id")
        self.pop = Input(1, "pop")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.head_addr = Output(64, "head_addr")
        self.head_id = Output(4, "head_id")

        self.cnt = Reg(3, "cnt")
        self.head = Reg(3, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(3, "tail")

        self.addr_t = Array(64, 8, "addr_t")
        self.id_t = Array(4, 8, "id_t")
        self.vld_t = Array(64, 8, "vld_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.empty <<= 1
                self.head_addr <<= 0
                self.head_id <<= 0
            with Else():
                self.full <<= (self.cnt >= 4)
                self.empty <<= (self.cnt == 0)
                self.head_addr <<= self.addr_t[self.head]
                self.head_id <<= self.id_t[self.head]

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.vld_t[0] <<= 0
                self.vld_t[1] <<= 0
                self.vld_t[2] <<= 0
                self.vld_t[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.push == 1) & (self.cnt < 4)):
                    self.addr_t[self.tail] <<= self.snoop_addr
                    self.id_t[self.tail] <<= self.snoop_id
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.pop == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1)):
                    self.vld_t[self.head] <<= 0
                    self.head <<= self.head + 1
                    self.cnt <<= self.cnt - 1
                with If((self.flush == 1)):
                    self.head <<= 0
                    self.tail <<= 0
                    self.cnt <<= 0
                    self.vld_t[0] <<= 0
                    self.vld_t[1] <<= 0
                    self.vld_t[2] <<= 0
                    self.vld_t[3] <<= 0


