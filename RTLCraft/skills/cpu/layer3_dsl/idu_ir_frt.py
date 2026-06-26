"""
L3 DSL — FRenameTable, FRenameTable.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class FRenameTable(Module):
    def __init__(self):
        super().__init__("frenametable")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.frs1 = Input(6, "frs1")
        self.frs2 = Input(6, "frs2")
        self.frd = Input(6, "frd")
        self.frd_phy = Input(6, "frd_phy")
        self.frd_we = Input(1, "frd_we")
        self.flush = Input(1, "flush")
        self.alloc = Input(1, "alloc")
        self.pfrs1 = Output(6, "pfrs1")
        self.pfrs2 = Output(6, "pfrs2")
        self.alloc_fphy = Output(6, "alloc_fphy")
        self.freelist_empty = Output(1, "freelist_empty")

        self.fl_cnt = Reg(6, "fl_cnt")
        self.fl_head = Reg(6, "fl_head")
        self.init = Reg(1, "init")

        self.fmap_t = Array(6, 64, "fmap_t")
        self.ffreelist = Array(6, 64, "ffreelist")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pfrs1 <<= 0
                self.pfrs2 <<= 0
                self.alloc_fphy <<= 0
                self.freelist_empty <<= 1
            with Else():
                self.pfrs1 <<= self.fmap_t[self.frs1]
                self.pfrs2 <<= self.fmap_t[self.frs2]
                self.alloc_fphy <<= self.ffreelist[self.fl_head]
                self.freelist_empty <<= (self.fl_cnt == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.fl_head <<= 0
                self.fl_cnt <<= 0
                self.fmap_t[0] <<= 0
                self.fmap_t[1] <<= 1
                self.fmap_t[2] <<= 2
                self.fmap_t[3] <<= 3
                self.fmap_t[4] <<= 4
                self.fmap_t[5] <<= 5
                self.fmap_t[6] <<= 6
                self.fmap_t[7] <<= 7
                self.fmap_t[8] <<= 8
                self.fmap_t[9] <<= 9
                self.fmap_t[10] <<= 10
                self.fmap_t[11] <<= 11
                self.fmap_t[12] <<= 12
                self.fmap_t[13] <<= 13
                self.fmap_t[14] <<= 14
                self.fmap_t[15] <<= 15
                self.fmap_t[16] <<= 16
                self.fmap_t[17] <<= 17
                self.fmap_t[18] <<= 18
                self.fmap_t[19] <<= 19
                self.fmap_t[20] <<= 20
                self.fmap_t[21] <<= 21
                self.fmap_t[22] <<= 22
                self.fmap_t[23] <<= 23
                self.fmap_t[24] <<= 24
                self.fmap_t[25] <<= 25
                self.fmap_t[26] <<= 26
                self.fmap_t[27] <<= 27
                self.fmap_t[28] <<= 28
                self.fmap_t[29] <<= 29
                self.fmap_t[30] <<= 30
                self.fmap_t[31] <<= 31
                self.fl_cnt <<= 0
            with Else():
                self.init <<= 1
                with If((self.frd_we == 1)):
                    self.fmap_t[self.frd] <<= self.frd_phy
                with If((1 & self.fl_cnt) > 0):
                    self.fl_head <<= self.fl_head + 1
                    self.fl_cnt <<= self.fl_cnt - 1


