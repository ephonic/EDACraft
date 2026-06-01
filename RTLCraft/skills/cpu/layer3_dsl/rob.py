"""
L3 DSL — ROB, ROB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ROB(Module):
    def __init__(self):
        super().__init__("rob")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.alloc = Input(1, "alloc")
        self.rd_phy = Input(7, "rd_phy")
        self.complete = Input(1, "complete")
        self.complete_idx = Input(6, "complete_idx")
        self.exception = Input(1, "exception")
        self.retire_ready = Input(1, "retire_ready")
        self.retire_rd = Output(7, "retire_rd")
        self.retire_en = Output(1, "retire_en")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.alloc_idx = Output(6, "alloc_idx")

        self.cnt = Reg(6, "cnt")
        self.head = Reg(6, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(6, "tail")

        self.pr_t = Array(7, 64, "pr_t")
        self.done_t = Array(1, 64, "done_t")
        self.exc_t = Array(64, 64, "exc_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.retire_rd <<= 0
                self.retire_en <<= 0
                self.full <<= 0
                self.empty <<= 1
                self.alloc_idx <<= 0
            with Else():
                self.retire_rd <<= self.pr_t[self.head]
                self.retire_en <<= (self.cnt > 0) & self.done_t[self.head]
                self.full <<= (self.cnt >= 32)
                self.empty <<= (self.cnt == 0)
                self.alloc_idx <<= self.tail

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.done_t[0] <<= 0
                self.exc_t[0] <<= 0
                self.done_t[1] <<= 0
                self.exc_t[1] <<= 0
                self.done_t[2] <<= 0
                self.exc_t[2] <<= 0
                self.done_t[3] <<= 0
                self.exc_t[3] <<= 0
                self.done_t[4] <<= 0
                self.exc_t[4] <<= 0
                self.done_t[5] <<= 0
                self.exc_t[5] <<= 0
                self.done_t[6] <<= 0
                self.exc_t[6] <<= 0
                self.done_t[7] <<= 0
                self.exc_t[7] <<= 0
                self.done_t[8] <<= 0
                self.exc_t[8] <<= 0
                self.done_t[9] <<= 0
                self.exc_t[9] <<= 0
                self.done_t[10] <<= 0
                self.exc_t[10] <<= 0
                self.done_t[11] <<= 0
                self.exc_t[11] <<= 0
                self.done_t[12] <<= 0
                self.exc_t[12] <<= 0
                self.done_t[13] <<= 0
                self.exc_t[13] <<= 0
                self.done_t[14] <<= 0
                self.exc_t[14] <<= 0
                self.done_t[15] <<= 0
                self.exc_t[15] <<= 0
                self.done_t[16] <<= 0
                self.exc_t[16] <<= 0
                self.done_t[17] <<= 0
                self.exc_t[17] <<= 0
                self.done_t[18] <<= 0
                self.exc_t[18] <<= 0
                self.done_t[19] <<= 0
                self.exc_t[19] <<= 0
                self.done_t[20] <<= 0
                self.exc_t[20] <<= 0
                self.done_t[21] <<= 0
                self.exc_t[21] <<= 0
                self.done_t[22] <<= 0
                self.exc_t[22] <<= 0
                self.done_t[23] <<= 0
                self.exc_t[23] <<= 0
                self.done_t[24] <<= 0
                self.exc_t[24] <<= 0
                self.done_t[25] <<= 0
                self.exc_t[25] <<= 0
                self.done_t[26] <<= 0
                self.exc_t[26] <<= 0
                self.done_t[27] <<= 0
                self.exc_t[27] <<= 0
                self.done_t[28] <<= 0
                self.exc_t[28] <<= 0
                self.done_t[29] <<= 0
                self.exc_t[29] <<= 0
                self.done_t[30] <<= 0
                self.exc_t[30] <<= 0
                self.done_t[31] <<= 0
                self.exc_t[31] <<= 0
            with Else():
                self.init <<= 1
                with If((self.alloc == 1) & (self.cnt < 32)):
                    self.pr_t[self.tail] <<= self.rd_phy
                    self.done_t[self.tail] <<= 0
                    self.exc_t[self.tail] <<= 0
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.complete == 1)):
                    self.done_t[self.complete_idx] <<= 1
                    self.exc_t[self.complete_idx] <<= self.exception
                with If((self.retire_ready == 1) & (self.cnt > 0) & (self.done_t[self.head] == 1)):
                    self.head <<= self.head + 1
                    self.cnt <<= self.cnt - 1


