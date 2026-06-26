"""
L3 DSL — StoreDataArray, StoreDataArray.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class StoreDataArray(Module):
    def __init__(self):
        super().__init__("storedataarray")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.wr_addr = Input(6, "wr_addr")
        self.way = Input(2, "way")
        self.wr_data = Input(64, "wr_data")
        self.byte_en = Input(8, "byte_en")
        self.wr_valid = Input(1, "wr_valid")
        self.ready = Output(1, "ready")

        self.wr_mask = Wire(64, "wr_mask")

        self.arr = Array(64, 256, "arr")

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If((self.wr_valid == 1)):
                self.arr[{self.way, self.wr_addr}] <<= self.arr[{self.way, self.wr_addr}] & ~self.wr_mask | self.wr_data & self.wr_mask


