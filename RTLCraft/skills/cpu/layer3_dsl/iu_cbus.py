"""
L3 DSL — ResultBus, ResultBus.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ResultBus(Module):
    def __init__(self):
        super().__init__("resultbus")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.issue_valid = Input(1, "issue_valid")
        self.issue_prd = Input(7, "issue_prd")
        self.result = Input(64, "result")
        self.complete = Input(1, "complete")
        self.retire = Input(1, "retire")
        self.wb_valid = Output(1, "wb_valid")
        self.wb_prd = Output(7, "wb_prd")
        self.wb_data = Output(64, "wb_data")
        self.busy = Output(1, "busy")

        self.data_r = Reg(64, "data_r")
        self.init = Reg(1, "init")
        self.prd_r = Reg(7, "prd_r")
        self.valid_r = Reg(1, "valid_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.wb_valid <<= 0
                self.wb_prd <<= 0
                self.wb_data <<= 0
                self.busy <<= 0
            with Else():
                self.wb_valid <<= self.valid_r
                self.wb_prd <<= self.prd_r
                self.wb_data <<= self.data_r
                self.busy <<= self.valid_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.valid_r <<= 0
                self.prd_r <<= 0
                self.data_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.retire == 1)):
                    self.valid_r <<= 0
                with If((self.complete == 1) & (self.issue_valid == 1)):
                    self.valid_r <<= 1
                    self.prd_r <<= self.issue_prd
                    self.data_r <<= self.result


