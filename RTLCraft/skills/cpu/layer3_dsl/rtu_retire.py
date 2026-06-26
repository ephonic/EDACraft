"""
L3 DSL — RetireUnit, RetireUnit.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class RetireUnit(Module):
    def __init__(self):
        super().__init__("retireunit")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rob_retire_rd = Input(7, "rob_retire_rd")
        self.rob_retire_en = Input(1, "rob_retire_en")
        self.rob_empty = Input(1, "rob_empty")
        self.commit_ready = Input(1, "commit_ready")
        self.alloc_pr = Input(7, "alloc_pr")
        self.alloc_ar = Input(6, "alloc_ar")
        self.alloc_en = Input(1, "alloc_en")
        self.retire_ar = Output(6, "retire_ar")
        self.retire_en = Output(1, "retire_en")
        self.retire_pd = Output(7, "retire_pd")
        self.flush = Output(1, "flush")

        self.init = Reg(1, "init")

        self.pr2ar = Array(6, 128, "pr2ar")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.retire_ar <<= 0
                self.retire_en <<= 0
                self.retire_pd <<= 0
                self.flush <<= 0
            with Else():
                self.retire_ar <<= self.pr2ar[self.rob_retire_rd]
                self.retire_en <<= (self.rob_retire_en == 1) & (self.rob_empty == 0) & (self.commit_ready == 1)
                self.retire_pd <<= self.rob_retire_rd
                self.flush <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pr2ar[0] <<= 0
                self.pr2ar[1] <<= 1
                self.pr2ar[2] <<= 2
                self.pr2ar[3] <<= 3
                self.pr2ar[4] <<= 4
                self.pr2ar[5] <<= 5
                self.pr2ar[6] <<= 6
                self.pr2ar[7] <<= 7
                self.pr2ar[8] <<= 8
                self.pr2ar[9] <<= 9
                self.pr2ar[10] <<= 10
                self.pr2ar[11] <<= 11
                self.pr2ar[12] <<= 12
                self.pr2ar[13] <<= 13
                self.pr2ar[14] <<= 14
                self.pr2ar[15] <<= 15
                self.pr2ar[16] <<= 16
                self.pr2ar[17] <<= 17
                self.pr2ar[18] <<= 18
                self.pr2ar[19] <<= 19
                self.pr2ar[20] <<= 20
                self.pr2ar[21] <<= 21
                self.pr2ar[22] <<= 22
                self.pr2ar[23] <<= 23
                self.pr2ar[24] <<= 24
                self.pr2ar[25] <<= 25
                self.pr2ar[26] <<= 26
                self.pr2ar[27] <<= 27
                self.pr2ar[28] <<= 28
                self.pr2ar[29] <<= 29
                self.pr2ar[30] <<= 30
                self.pr2ar[31] <<= 31
                self.pr2ar[32] <<= 0
                self.pr2ar[33] <<= 1
                self.pr2ar[34] <<= 2
                self.pr2ar[35] <<= 3
                self.pr2ar[36] <<= 4
                self.pr2ar[37] <<= 5
                self.pr2ar[38] <<= 6
                self.pr2ar[39] <<= 7
                self.pr2ar[40] <<= 8
                self.pr2ar[41] <<= 9
                self.pr2ar[42] <<= 10
                self.pr2ar[43] <<= 11
                self.pr2ar[44] <<= 12
                self.pr2ar[45] <<= 13
                self.pr2ar[46] <<= 14
                self.pr2ar[47] <<= 15
                self.pr2ar[48] <<= 16
                self.pr2ar[49] <<= 17
                self.pr2ar[50] <<= 18
                self.pr2ar[51] <<= 19
                self.pr2ar[52] <<= 20
                self.pr2ar[53] <<= 21
                self.pr2ar[54] <<= 22
                self.pr2ar[55] <<= 23
                self.pr2ar[56] <<= 24
                self.pr2ar[57] <<= 25
                self.pr2ar[58] <<= 26
                self.pr2ar[59] <<= 27
                self.pr2ar[60] <<= 28
                self.pr2ar[61] <<= 29
                self.pr2ar[62] <<= 30
                self.pr2ar[63] <<= 31
            with Else():
                self.init <<= 1
                with If((self.alloc_en == 1)):
                    self.pr2ar[self.alloc_pr] <<= self.alloc_ar


