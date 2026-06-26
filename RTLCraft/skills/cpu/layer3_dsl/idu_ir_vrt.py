"""
L3 DSL — VRenameTable, VRenameTable.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class VRenameTable(Module):
    def __init__(self):
        super().__init__("vrenametable")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.vrs1 = Input(6, "vrs1")
        self.vrs2 = Input(6, "vrs2")
        self.vrd = Input(6, "vrd")
        self.vrd_phy = Input(6, "vrd_phy")
        self.vrd_we = Input(1, "vrd_we")
        self.flush = Input(1, "flush")
        self.alloc = Input(1, "alloc")
        self.pvrs1 = Output(6, "pvrs1")
        self.pvrs2 = Output(6, "pvrs2")
        self.alloc_vphy = Output(6, "alloc_vphy")
        self.freelist_empty = Output(1, "freelist_empty")

        self.fl_cnt = Reg(6, "fl_cnt")
        self.fl_head = Reg(6, "fl_head")
        self.init = Reg(1, "init")

        self.vmap_t = Array(6, 64, "vmap_t")
        self.vfreelist = Array(6, 64, "vfreelist")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pvrs1 <<= 0
                self.pvrs2 <<= 0
                self.alloc_vphy <<= 0
                self.freelist_empty <<= 1
            with Else():
                self.pvrs1 <<= self.vmap_t[self.vrs1]
                self.pvrs2 <<= self.vmap_t[self.vrs2]
                self.alloc_vphy <<= self.vfreelist[self.fl_head]
                self.freelist_empty <<= (self.fl_cnt == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.fl_head <<= 0
                self.fl_cnt <<= 0
                self.vmap_t[0] <<= 0
                self.vmap_t[1] <<= 1
                self.vmap_t[2] <<= 2
                self.vmap_t[3] <<= 3
                self.vmap_t[4] <<= 4
                self.vmap_t[5] <<= 5
                self.vmap_t[6] <<= 6
                self.vmap_t[7] <<= 7
                self.vmap_t[8] <<= 8
                self.vmap_t[9] <<= 9
                self.vmap_t[10] <<= 10
                self.vmap_t[11] <<= 11
                self.vmap_t[12] <<= 12
                self.vmap_t[13] <<= 13
                self.vmap_t[14] <<= 14
                self.vmap_t[15] <<= 15
                self.vmap_t[16] <<= 16
                self.vmap_t[17] <<= 17
                self.vmap_t[18] <<= 18
                self.vmap_t[19] <<= 19
                self.vmap_t[20] <<= 20
                self.vmap_t[21] <<= 21
                self.vmap_t[22] <<= 22
                self.vmap_t[23] <<= 23
                self.vmap_t[24] <<= 24
                self.vmap_t[25] <<= 25
                self.vmap_t[26] <<= 26
                self.vmap_t[27] <<= 27
                self.vmap_t[28] <<= 28
                self.vmap_t[29] <<= 29
                self.vmap_t[30] <<= 30
                self.vmap_t[31] <<= 31
                self.fl_cnt <<= 0
            with Else():
                self.init <<= 1
                with If((self.vrd_we == 1)):
                    self.vmap_t[self.vrd] <<= self.vrd_phy
                with If((1 & self.fl_cnt) > 0):
                    self.fl_head <<= self.fl_head + 1
                    self.fl_cnt <<= self.fl_cnt - 1


