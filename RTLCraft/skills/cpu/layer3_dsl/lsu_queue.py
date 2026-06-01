"""
L3 DSL — LoadQueue, StoreQueue, LoadQueue, StoreQueue.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LoadQueue(Module):
    def __init__(self):
        super().__init__("loadqueue")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.addr = Input(64, "addr")
        self.wakeup = Input(1, "wakeup")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.pending = Output(1, "pending")

        self.cnt = Reg(4, "cnt")
        self.head = Reg(4, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(4, "tail")

        self.vld_t = Array(64, 16, "vld_t")
        self.addr_t = Array(64, 16, "addr_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.empty <<= 1
                self.pending <<= 0
            with Else():
                self.full <<= (self.cnt >= 8)
                self.empty <<= (self.cnt == 0)
                self.pending <<= (self.cnt > 0)

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
                self.vld_t[4] <<= 0
                self.vld_t[5] <<= 0
                self.vld_t[6] <<= 0
                self.vld_t[7] <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1) & (self.cnt < 8)):
                    self.addr_t[self.tail] <<= self.addr
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.wakeup == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1)):
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
                    self.vld_t[4] <<= 0
                    self.vld_t[5] <<= 0
                    self.vld_t[6] <<= 0
                    self.vld_t[7] <<= 0


class StoreQueue(Module):
    def __init__(self):
        super().__init__("storequeue")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.addr = Input(64, "addr")
        self.data = Input(64, "data")
        self.commit = Input(1, "commit")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.commit_data = Output(64, "commit_data")
        self.commit_addr = Output(64, "commit_addr")
        self.commit_valid = Output(1, "commit_valid")

        self.cnt = Reg(4, "cnt")
        self.head = Reg(4, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(4, "tail")

        self.data_t = Array(64, 16, "data_t")
        self.addr_t = Array(64, 16, "addr_t")
        self.vld_t = Array(1, 16, "vld_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.empty <<= 1
                self.commit_data <<= 0
                self.commit_addr <<= 0
                self.commit_valid <<= 0
            with Else():
                self.full <<= (self.cnt >= 8)
                self.empty <<= (self.cnt == 0)
                self.commit_data <<= self.data_t[self.head]
                self.commit_addr <<= self.addr_t[self.head]
                self.commit_valid <<= (self.cnt > 0) & (self.vld_t[self.head] == 1)

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
                self.vld_t[4] <<= 0
                self.vld_t[5] <<= 0
                self.vld_t[6] <<= 0
                self.vld_t[7] <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1) & (self.cnt < 8)):
                    self.addr_t[self.tail] <<= self.addr
                    self.data_t[self.tail] <<= self.data
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.commit == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1)):
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
                    self.vld_t[4] <<= 0
                    self.vld_t[5] <<= 0
                    self.vld_t[6] <<= 0
                    self.vld_t[7] <<= 0


