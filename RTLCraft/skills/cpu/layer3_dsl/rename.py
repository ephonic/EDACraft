"""
L3 DSL — RenameTable, RenameTable.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class RenameTable(Module):
    def __init__(self):
        super().__init__("renametable")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rs1 = Input(6, "rs1")
        self.rs2 = Input(6, "rs2")
        self.rd = Input(6, "rd")
        self.rd_phy = Input(7, "rd_phy")
        self.rd_we = Input(1, "rd_we")
        self.flush = Input(1, "flush")
        self.alloc = Input(1, "alloc")
        self.prs1 = Output(7, "prs1")
        self.prs2 = Output(7, "prs2")
        self.alloc_phy = Output(7, "alloc_phy")
        self.freelist_empty = Output(1, "freelist_empty")

        self.fl_cnt = Reg(7, "fl_cnt")
        self.fl_head = Reg(7, "fl_head")
        self.init = Reg(1, "init")

        self.map_t = Array(7, 64, "map_t")
        self.freelist = Array(7, 128, "freelist")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.prs1 <<= 0
                self.prs2 <<= 0
                self.alloc_phy <<= 0
                self.freelist_empty <<= 1
            with Else():
                self.prs1 <<= self.map_t[self.rs1]
                self.prs2 <<= self.map_t[self.rs2]
                self.alloc_phy <<= self.freelist[self.fl_head]
                self.freelist_empty <<= (self.fl_cnt == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.fl_head <<= 0
                self.fl_cnt <<= 0
                self.map_t[0] <<= 0
                self.map_t[1] <<= 1
                self.map_t[2] <<= 2
                self.map_t[3] <<= 3
                self.map_t[4] <<= 4
                self.map_t[5] <<= 5
                self.map_t[6] <<= 6
                self.map_t[7] <<= 7
                self.map_t[8] <<= 8
                self.map_t[9] <<= 9
                self.map_t[10] <<= 10
                self.map_t[11] <<= 11
                self.map_t[12] <<= 12
                self.map_t[13] <<= 13
                self.map_t[14] <<= 14
                self.map_t[15] <<= 15
                self.map_t[16] <<= 16
                self.map_t[17] <<= 17
                self.map_t[18] <<= 18
                self.map_t[19] <<= 19
                self.map_t[20] <<= 20
                self.map_t[21] <<= 21
                self.map_t[22] <<= 22
                self.map_t[23] <<= 23
                self.map_t[24] <<= 24
                self.map_t[25] <<= 25
                self.map_t[26] <<= 26
                self.map_t[27] <<= 27
                self.map_t[28] <<= 28
                self.map_t[29] <<= 29
                self.map_t[30] <<= 30
                self.map_t[31] <<= 31
                self.freelist[0] <<= 32
                self.freelist[1] <<= 33
                self.freelist[2] <<= 34
                self.freelist[3] <<= 35
                self.freelist[4] <<= 36
                self.freelist[5] <<= 37
                self.freelist[6] <<= 38
                self.freelist[7] <<= 39
                self.freelist[8] <<= 40
                self.freelist[9] <<= 41
                self.freelist[10] <<= 42
                self.freelist[11] <<= 43
                self.freelist[12] <<= 44
                self.freelist[13] <<= 45
                self.freelist[14] <<= 46
                self.freelist[15] <<= 47
                self.freelist[16] <<= 48
                self.freelist[17] <<= 49
                self.freelist[18] <<= 50
                self.freelist[19] <<= 51
                self.freelist[20] <<= 52
                self.freelist[21] <<= 53
                self.freelist[22] <<= 54
                self.freelist[23] <<= 55
                self.freelist[24] <<= 56
                self.freelist[25] <<= 57
                self.freelist[26] <<= 58
                self.freelist[27] <<= 59
                self.freelist[28] <<= 60
                self.freelist[29] <<= 61
                self.freelist[30] <<= 62
                self.freelist[31] <<= 63
                self.fl_cnt <<= 32
            with Else():
                self.init <<= 1
                with If((self.rd_we == 1)):
                    self.map_t[self.rd] <<= self.rd_phy
                with If((self.alloc == 1) & (self.fl_cnt > 0)):
                    self.fl_head <<= self.fl_head + 1
                    self.fl_cnt <<= self.fl_cnt - 1


