"""
L3 DSL — WMB, WMB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class WMB(Module):
    def __init__(self):
        super().__init__("wmb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.addr = Input(64, "addr")
        self.data = Input(64, "data")
        self.size = Input(3, "size")
        self.drain = Input(1, "drain")
        self.flush = Input(1, "flush")
        self.full = Output(1, "full")
        self.merge_addr = Output(64, "merge_addr")
        self.merge_data = Output(128, "merge_data")
        self.merge_valid = Output(1, "merge_valid")
        self.busy = Output(1, "busy")

        self.cnt = Reg(3, "cnt")
        self.half_sel = Wire(1, "half_sel")
        self.head = Reg(3, "head")
        self.init = Reg(1, "init")
        self.line_addr = Wire(60, "line_addr")
        self.ma_r = Reg(64, "ma_r")
        self.md_r = Reg(128, "md_r")
        self.mv_r = Reg(1, "mv_r")
        self.tail = Reg(3, "tail")

        self.vld = Array(1, 4, "vld")
        self.eaddr = Array(60, 4, "eaddr")
        self.edata = Array(128, 4, "edata")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.full <<= 0
                self.merge_addr <<= 0
                self.merge_data <<= 0
                self.merge_valid <<= 0
                self.busy <<= 0
            with Else():
                self.full <<= (self.cnt >= 4)
                self.busy <<= (self.cnt > 0)
                self.merge_addr <<= self.ma_r
                self.merge_data <<= self.md_r
                self.merge_valid <<= self.mv_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.mv_r <<= 0
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
                    self.mv_r <<= 0
                    self.vld[0] <<= 0
                    self.vld[1] <<= 0
                    self.vld[2] <<= 0
                    self.vld[3] <<= 0
                with Else():
                    with If((self.drain == 1) & (self.cnt > 0)):
                        self.mv_r <<= 1
                        self.ma_r <<= self.eaddr[self.head] << 4
                        self.md_r <<= self.edata[self.head]
                        self.vld[self.head] <<= 0
                        self.head <<= self.head + 1
                        self.cnt <<= self.cnt - 1
                    with Else():
                        self.mv_r <<= 0
                    with If((self.enqueue == 1) & (self.cnt < 4)):
                        with If(((self.vld[0] == 1) & (self.eaddr[0] == self.line_addr) | (self.vld[1] == 1) & (self.eaddr[1] == self.line_addr) | (self.vld[2] == 1) & (self.eaddr[2] == self.line_addr) | (self.vld[3] == 1) & (self.eaddr[3] == self.line_addr)) == 1):
                            with If(((self.vld[0] == 1) & (self.eaddr[0] == self.line_addr)) == 1):
                                with If((self.half_sel == 0)):
                                    self.edata[0] <<= self.edata[0] & 340282366920938463444927863358058659840 | self.data
                                with Else():
                                    self.edata[0] <<= self.edata[0] & 18446744073709551615 | {self.data, 0}
                            with Elif(((self.vld[1] == 1) & (self.eaddr[1] == self.line_addr)) == 1):
                                with If((self.half_sel == 0)):
                                    self.edata[1] <<= self.edata[1] & 340282366920938463444927863358058659840 | self.data
                                with Else():
                                    self.edata[1] <<= self.edata[1] & 18446744073709551615 | {self.data, 0}
                            with Elif(((self.vld[2] == 1) & (self.eaddr[2] == self.line_addr)) == 1):
                                with If((self.half_sel == 0)):
                                    self.edata[2] <<= self.edata[2] & 340282366920938463444927863358058659840 | self.data
                                with Else():
                                    self.edata[2] <<= self.edata[2] & 18446744073709551615 | {self.data, 0}
                            with Elif(((self.vld[3] == 1) & (self.eaddr[3] == self.line_addr)) == 1):
                                with If((self.half_sel == 0)):
                                    self.edata[3] <<= self.edata[3] & 340282366920938463444927863358058659840 | self.data
                                with Else():
                                    self.edata[3] <<= self.edata[3] & 18446744073709551615 | {self.data, 0}
                        with Else():
                            self.vld[self.tail] <<= 1
                            self.eaddr[self.tail] <<= self.line_addr
                            with If((self.half_sel == 0)):
                                self.edata[self.tail] <<= self.data
                            with Else():
                                self.edata[self.tail] <<= Cat(self.data, 0)
                            self.tail <<= self.tail + 1
                            self.cnt <<= self.cnt + 1


