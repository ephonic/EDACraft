"""
L3 DSL — VBStoreData, VBStoreData.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class VBStoreData(Module):
    def __init__(self):
        super().__init__("vbstoredata")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.wr_addr = Input(6, "wr_addr")
        self.wr_data = Input(128, "wr_data")
        self.wr_valid = Input(1, "wr_valid")
        self.rd_addr = Input(6, "rd_addr")
        self.rd_req = Input(1, "rd_req")
        self.rd_data = Output(128, "rd_data")
        self.rd_valid = Output(1, "rd_valid")

        self.init = Reg(1, "init")
        self.rd_data_r = Reg(128, "rd_data_r")
        self.rd_valid_r = Reg(1, "rd_valid_r")

        self.vb_sdb_arr = Array(128, 64, "vb_sdb_arr")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rd_data <<= 0
                self.rd_valid <<= 0
            with Else():
                self.rd_data <<= self.rd_data_r
                self.rd_valid <<= self.rd_valid_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.rd_data_r <<= 0
                self.rd_valid_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.wr_valid == 1)):
                    self.vb_sdb_arr[self.wr_addr] <<= self.wr_data
                with If((self.rd_req == 1)):
                    self.rd_data_r <<= self.vb_sdb_arr[self.rd_addr]
                    self.rd_valid_r <<= 1
                with Else():
                    self.rd_valid_r <<= 0


