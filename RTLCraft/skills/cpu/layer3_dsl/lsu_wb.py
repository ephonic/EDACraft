"""
L3 DSL — LoadWriteback, StoreWriteback, LoadWriteback, StoreWriteback.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LoadWriteback(Module):
    def __init__(self):
        super().__init__("loadwriteback")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.lsu_result = Input(64, "lsu_result")
        self.lsu_valid = Input(1, "lsu_valid")
        self.rob_ready = Input(1, "rob_ready")
        self.wb_data = Output(64, "wb_data")
        self.wb_valid = Output(1, "wb_valid")
        self.busy = Output(1, "busy")

        self.data_r = Reg(64, "data_r")
        self.init = Reg(1, "init")
        self.valid_r = Reg(1, "valid_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.wb_data <<= 0
                self.wb_valid <<= 0
                self.busy <<= 1
            with Else():
                self.wb_data <<= self.data_r
                self.wb_valid <<= self.valid_r
                self.busy <<= (self.lsu_valid == 1) & (self.rob_ready == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.valid_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.lsu_valid == 1) & (self.rob_ready == 1)):
                    self.data_r <<= self.lsu_result
                    self.valid_r <<= 1
                with Elif((self.rob_ready == 1)):
                    self.valid_r <<= 0


class StoreWriteback(Module):
    def __init__(self):
        super().__init__("storewriteback")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.sq_data = Input(64, "sq_data")
        self.sq_addr = Input(64, "sq_addr")
        self.sq_valid = Input(1, "sq_valid")
        self.dcache_ready = Input(1, "dcache_ready")
        self.wb_data = Output(64, "wb_data")
        self.wb_addr = Output(64, "wb_addr")
        self.wb_valid = Output(1, "wb_valid")
        self.busy = Output(1, "busy")

        self.addr_r = Reg(64, "addr_r")
        self.data_r = Reg(64, "data_r")
        self.init = Reg(1, "init")
        self.valid_r = Reg(1, "valid_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.wb_data <<= 0
                self.wb_addr <<= 0
                self.wb_valid <<= 0
                self.busy <<= 1
            with Else():
                self.wb_data <<= self.data_r
                self.wb_addr <<= self.addr_r
                self.wb_valid <<= self.valid_r
                self.busy <<= (self.sq_valid == 1) & (self.dcache_ready == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.valid_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.sq_valid == 1) & (self.dcache_ready == 1)):
                    self.data_r <<= self.sq_data
                    self.addr_r <<= self.sq_addr
                    self.valid_r <<= 1
                with Elif((self.dcache_ready == 1)):
                    self.valid_r <<= 0


