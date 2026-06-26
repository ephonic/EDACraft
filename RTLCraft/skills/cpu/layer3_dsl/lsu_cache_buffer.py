"""
L3 DSL — CacheBuffer, CacheBuffer.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class CacheBuffer(Module):
    def __init__(self):
        super().__init__("cachebuffer")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.fill_data = Input(128, "fill_data")
        self.fill_valid = Input(1, "fill_valid")
        self.drain = Input(1, "drain")
        self.flush = Input(1, "flush")
        self.data = Output(128, "data")
        self.valid = Output(1, "valid")
        self.empty = Output(1, "empty")

        self.cnt = Reg(2, "cnt")
        self.init = Reg(1, "init")
        self.rd_ptr = Reg(1, "rd_ptr")
        self.wr_ptr = Reg(1, "wr_ptr")

        self.buf_data = Array(128, 2, "buf_data")
        self.buf_vld = Array(1, 2, "buf_vld")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.data <<= 0
                self.valid <<= 0
                self.empty <<= 1
            with Else():
                with If((self.cnt > 0) & (self.buf_vld[self.rd_ptr] == 1)):
                    self.data <<= self.buf_data[self.rd_ptr]
                    self.valid <<= 1
                with Else():
                    self.data <<= 0
                    self.valid <<= 0
                self.empty <<= (self.cnt == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.wr_ptr <<= 0
                self.rd_ptr <<= 0
                self.cnt <<= 0
                self.buf_vld[0] <<= 0
                self.buf_vld[1] <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.wr_ptr <<= 0
                    self.rd_ptr <<= 0
                    self.cnt <<= 0
                    self.buf_vld[0] <<= 0
                    self.buf_vld[1] <<= 0
                with Else():
                    with If((self.fill_valid == 1) & (self.cnt < 2)):
                        self.buf_data[self.wr_ptr] <<= self.fill_data
                        self.buf_vld[self.wr_ptr] <<= 1
                        self.wr_ptr <<= self.wr_ptr + 1
                        self.cnt <<= self.cnt + 1
                    with If((self.drain == 1) & (self.cnt > 0)):
                        self.buf_vld[self.rd_ptr] <<= 0
                        self.rd_ptr <<= self.rd_ptr + 1
                        self.cnt <<= self.cnt - 1


