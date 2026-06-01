"""
L3 DSL — CommitUnit, CommitUnit.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class CommitUnit(Module):
    def __init__(self):
        super().__init__("commitunit")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.retire_ar = Input(6, "retire_ar")
        self.retire_pr = Input(7, "retire_pr")
        self.retire_en = Input(1, "retire_en")
        self.flush = Input(1, "flush")
        self.commit_ar = Output(6, "commit_ar")
        self.commit_pr = Output(7, "commit_pr")
        self.commit_en = Output(1, "commit_en")

        self.init = Reg(1, "init")

        self.ar_map = Array(64, 32, "ar_map")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.commit_ar <<= 0
                self.commit_pr <<= 0
                self.commit_en <<= 0
            with Else():
                self.commit_ar <<= self.retire_ar
                self.commit_pr <<= self.retire_pr
                self.commit_en <<= self.retire_en

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.ar_map[0] <<= 0
                self.ar_map[1] <<= 1
                self.ar_map[2] <<= 2
                self.ar_map[3] <<= 3
                self.ar_map[4] <<= 4
                self.ar_map[5] <<= 5
                self.ar_map[6] <<= 6
                self.ar_map[7] <<= 7
                self.ar_map[8] <<= 8
                self.ar_map[9] <<= 9
                self.ar_map[10] <<= 10
                self.ar_map[11] <<= 11
                self.ar_map[12] <<= 12
                self.ar_map[13] <<= 13
                self.ar_map[14] <<= 14
                self.ar_map[15] <<= 15
                self.ar_map[16] <<= 16
                self.ar_map[17] <<= 17
                self.ar_map[18] <<= 18
                self.ar_map[19] <<= 19
                self.ar_map[20] <<= 20
                self.ar_map[21] <<= 21
                self.ar_map[22] <<= 22
                self.ar_map[23] <<= 23
                self.ar_map[24] <<= 24
                self.ar_map[25] <<= 25
                self.ar_map[26] <<= 26
                self.ar_map[27] <<= 27
                self.ar_map[28] <<= 28
                self.ar_map[29] <<= 29
                self.ar_map[30] <<= 30
                self.ar_map[31] <<= 31
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.ar_map[0] <<= 0
                    self.ar_map[1] <<= 1
                    self.ar_map[2] <<= 2
                    self.ar_map[3] <<= 3
                    self.ar_map[4] <<= 4
                    self.ar_map[5] <<= 5
                    self.ar_map[6] <<= 6
                    self.ar_map[7] <<= 7
                    self.ar_map[8] <<= 8
                    self.ar_map[9] <<= 9
                    self.ar_map[10] <<= 10
                    self.ar_map[11] <<= 11
                    self.ar_map[12] <<= 12
                    self.ar_map[13] <<= 13
                    self.ar_map[14] <<= 14
                    self.ar_map[15] <<= 15
                    self.ar_map[16] <<= 16
                    self.ar_map[17] <<= 17
                    self.ar_map[18] <<= 18
                    self.ar_map[19] <<= 19
                    self.ar_map[20] <<= 20
                    self.ar_map[21] <<= 21
                    self.ar_map[22] <<= 22
                    self.ar_map[23] <<= 23
                    self.ar_map[24] <<= 24
                    self.ar_map[25] <<= 25
                    self.ar_map[26] <<= 26
                    self.ar_map[27] <<= 27
                    self.ar_map[28] <<= 28
                    self.ar_map[29] <<= 29
                    self.ar_map[30] <<= 30
                    self.ar_map[31] <<= 31
                with Elif((self.retire_en == 1)):
                    self.ar_map[self.retire_ar] <<= self.retire_pr


