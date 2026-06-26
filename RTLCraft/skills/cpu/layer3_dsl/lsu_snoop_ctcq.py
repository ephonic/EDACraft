"""
L3 DSL — SnoopCtrlTQ, SnoopCtrlTQ.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SnoopCtrlTQ(Module):
    def __init__(self):
        super().__init__("snoopctrltq")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.snoop_addr = Input(64, "snoop_addr")
        self.snoop_type = Input(2, "snoop_type")
        self.dequeue = Input(1, "dequeue")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.head_addr = Output(64, "head_addr")
        self.head_type = Output(2, "head_type")

        self.cnt = Reg(3, "cnt")
        self.head = Reg(3, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(3, "tail")

        self.addr_t = Array(64, 8, "addr_t")
        self.type_t = Array(2, 8, "type_t")
        self.vld_t = Array(64, 8, "vld_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.empty <<= 1
                self.head_addr <<= 0
                self.head_type <<= 0
            with Else():
                self.full <<= (self.cnt >= 4)
                self.empty <<= (self.cnt == 0)
                self.head_addr <<= self.addr_t[self.head]
                self.head_type <<= self.type_t[self.head]

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
                with If((self.enqueue == 1) & (self.cnt < 4)):
                    self.addr_t[self.tail] <<= self.snoop_addr
                    self.type_t[self.tail] <<= self.snoop_type
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.dequeue == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1)):
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


