"""
L3 DSL — PCFifo, PCFifo.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PCFifo(Module):
    def __init__(self):
        super().__init__("pcfifo")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.push_pc = Input(39, "push_pc")
        self.push_valid = Input(1, "push_valid")
        self.pop = Input(1, "pop")
        self.flush = Input(1, "flush")
        self.top_pc = Output(39, "top_pc")
        self.top_valid = Output(1, "top_valid")
        self.free = Output(4, "free")

        self.init = Reg(1, "init")
        self.pcfifo_cnt = Reg(4, "pcfifo_cnt")
        self.pcfifo_rd = Reg(3, "pcfifo_rd")
        self.pcfifo_wr = Reg(3, "pcfifo_wr")

        self.pcfifo_mem = Array(39, 8, "pcfifo_mem")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.top_pc <<= 0
                self.top_valid <<= 0
                self.free <<= 0
            with Else():
                self.top_pc <<= self.pcfifo_mem[self.pcfifo_rd]
                self.top_valid <<= (self.pcfifo_cnt != 0)
                self.free <<= 8 - self.pcfifo_cnt

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pcfifo_wr <<= 0
                self.pcfifo_rd <<= 0
                self.pcfifo_cnt <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.pcfifo_wr <<= 0
                    self.pcfifo_rd <<= 0
                    self.pcfifo_cnt <<= 0
                with Else():
                    with If((self.push_valid == 1) & (self.pcfifo_cnt < 8)):
                        self.pcfifo_mem[self.pcfifo_wr] <<= self.push_pc
                        self.pcfifo_wr <<= self.pcfifo_wr + 1
                        self.pcfifo_cnt <<= self.pcfifo_cnt + 1
                    with If((self.pop == 1) & (self.pcfifo_cnt > 0)):
                        self.pcfifo_rd <<= self.pcfifo_rd + 1
                        self.pcfifo_cnt <<= self.pcfifo_cnt - 1


