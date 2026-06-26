"""
L3 DSL — LSReorderBuf, LSReorderBuf.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LSReorderBuf(Module):
    def __init__(self):
        super().__init__("lsreorderbuf")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ld_enqueue = Input(1, "ld_enqueue")
        self.ld_addr = Input(64, "ld_addr")
        self.st_enqueue = Input(1, "st_enqueue")
        self.st_addr = Input(64, "st_addr")
        self.st_data = Input(64, "st_data")
        self.complete = Input(1, "complete")
        self.complete_addr = Input(64, "complete_addr")
        self.flush = Input(1, "flush")
        self.ld_bypass_data = Output(64, "ld_bypass_data")
        self.ld_bypass_valid = Output(1, "ld_bypass_valid")
        self.st_forward_stall = Output(1, "st_forward_stall")
        self.busy = Output(1, "busy")

        self.cnt = Reg(3, "cnt")
        self.init = Reg(1, "init")
        self.match = Wire(1, "match")
        self.match_data = Wire(64, "match_data")
        self.tail = Reg(3, "tail")

        self.st_data_t = Array(64, 8, "st_data_t")
        self.st_vld_t = Array(64, 8, "st_vld_t")
        self.st_addr_t = Array(64, 8, "st_addr_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.ld_bypass_data <<= 0
                self.ld_bypass_valid <<= 0
                self.st_forward_stall <<= 0
                self.busy <<= 0
                self.match <<= 0
                self.match_data <<= 0
            with Else():
                self.busy <<= (self.cnt > 0)
                self.match <<= 0
                self.match_data <<= 0
                with If((self.st_vld_t[0] == 1) & (self.st_addr_t[0] == self.ld_addr)):
                    self.match <<= 1
                    self.match_data <<= self.st_data_t[0]
                with If((self.st_vld_t[1] == 1) & (self.st_addr_t[1] == self.ld_addr)):
                    self.match <<= 1
                    self.match_data <<= self.st_data_t[1]
                with If((self.st_vld_t[2] == 1) & (self.st_addr_t[2] == self.ld_addr)):
                    self.match <<= 1
                    self.match_data <<= self.st_data_t[2]
                with If((self.st_vld_t[3] == 1) & (self.st_addr_t[3] == self.ld_addr)):
                    self.match <<= 1
                    self.match_data <<= self.st_data_t[3]
                self.ld_bypass_valid <<= self.match & self.ld_enqueue
                self.ld_bypass_data <<= self.match_data
                self.st_forward_stall <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.st_vld_t[0] <<= 0
                self.st_vld_t[1] <<= 0
                self.st_vld_t[2] <<= 0
                self.st_vld_t[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.tail <<= 0
                    self.cnt <<= 0
                    self.st_vld_t[0] <<= 0
                    self.st_vld_t[1] <<= 0
                    self.st_vld_t[2] <<= 0
                    self.st_vld_t[3] <<= 0
                with Else():
                    with If((self.st_enqueue == 1) & (self.cnt < 4)):
                        self.st_addr_t[self.tail] <<= self.st_addr
                        self.st_data_t[self.tail] <<= self.st_data
                        self.st_vld_t[self.tail] <<= 1
                        self.tail <<= self.tail + 1
                        self.cnt <<= self.cnt + 1
                    with If((self.complete == 1) & (self.cnt > 0)):
                        with If((self.st_vld_t[0] == 1) & (self.st_addr_t[0] == self.complete_addr)):
                            self.st_vld_t[0] <<= 0
                        with If((self.st_vld_t[1] == 1) & (self.st_addr_t[1] == self.complete_addr)):
                            self.st_vld_t[1] <<= 0
                        with If((self.st_vld_t[2] == 1) & (self.st_addr_t[2] == self.complete_addr)):
                            self.st_vld_t[2] <<= 0
                        with If((self.st_vld_t[3] == 1) & (self.st_addr_t[3] == self.complete_addr)):
                            self.st_vld_t[3] <<= 0
                        self.cnt <<= self.cnt - 1


