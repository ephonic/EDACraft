"""
L3 DSL — IBuf, IBuf, IBuf, IBuf.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class IBuf(Module):
    def __init__(self):
        super().__init__("ibuf")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.push_valid = Input(1, "push_valid")
        self.push_data = Input(32, "push_data")
        self.pop_ready = Input(1, "pop_ready")
        self.data = Output(32, "data")
        self.valid = Output(1, "valid")
        self.stall = Output(1, "stall")

        self.bp_d = Reg(32, "bp_d")
        self.bp_v = Reg(1, "bp_v")
        self.cnt = Reg(4, "cnt")
        self.init = Reg(1, "init")
        self.pd_d = Reg(32, "pd_d")
        self.pd_v = Reg(1, "pd_v")
        self.rd = Reg(3, "rd")
        self.wr = Reg(3, "wr")

        self.mem = Array(32, 8, "mem")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.data <<= 0
                self.valid <<= 0
                self.stall <<= 0
            with Else():
                with If((self.cnt != 0) == 1):
                    self.data <<= self.mem[self.rd]
                    self.valid <<= 1
                with Elif((self.pd_v == 1)):
                    self.data <<= self.pd_d
                    self.valid <<= 1
                with Elif((self.bp_v == 1)):
                    self.data <<= self.bp_d
                    self.valid <<= 1
                with Else():
                    self.valid <<= 0
                self.stall <<= (self.cnt >= 8) & (self.push_valid == 1)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.wr <<= 0
                self.rd <<= 0
                self.cnt <<= 0
                self.bp_v <<= 0
                self.pd_v <<= 0
            with Else():
                self.init <<= 1
                self.pd_v <<= 0
                with If((self.push_valid == 1) & (self.cnt < 8)):
                    self.mem[self.wr] <<= self.push_data
                    self.wr <<= self.wr + 1
                    self.cnt <<= self.cnt + 1
                with If((self.pop_ready == 1) & (self.cnt > 0)):
                    self.pd_d <<= self.mem[self.rd]
                    self.pd_v <<= 1
                    self.rd <<= self.rd + 1
                    self.cnt <<= self.cnt - 1
                with If((self.push_valid == 1) & (self.pop_ready == 0)):
                    self.bp_v <<= 1
                    self.bp_d <<= self.push_data
                with Elif((self.pop_ready == 1)):
                    self.bp_v <<= 0


