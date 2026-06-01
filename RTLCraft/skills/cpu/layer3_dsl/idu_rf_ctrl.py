"""
L3 DSL — RFReadCtrl, RFWriteCtrl, RFReadCtrl, RFWriteCtrl.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class RFReadCtrl(Module):
    def __init__(self):
        super().__init__("rfreadctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pr_addr1 = Input(7, "pr_addr1")
        self.pr_addr2 = Input(7, "pr_addr2")
        self.pr_waddr = Input(7, "pr_waddr")
        self.pr_wdata = Input(64, "pr_wdata")
        self.pr_we = Input(1, "pr_we")
        self.rdata1 = Output(64, "rdata1")
        self.rdata2 = Output(64, "rdata2")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rdata1 <<= 0
                self.rdata2 <<= 0
            with Else():
                with If(((self.pr_we == 1) & (self.pr_addr1 == self.pr_waddr) & (self.pr_addr1 != 0)) == 1):
                    self.rdata1 <<= self.pr_wdata
                with Else():
                    self.rdata1 <<= 0
                with If(((self.pr_we == 1) & (self.pr_addr2 == self.pr_waddr) & (self.pr_addr2 != 0)) == 1):
                    self.rdata2 <<= self.pr_wdata
                with Else():
                    self.rdata2 <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


class RFWriteCtrl(Module):
    def __init__(self):
        super().__init__("rfwritectrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pr_waddr = Input(7, "pr_waddr")
        self.pr_wdata = Input(64, "pr_wdata")
        self.we = Input(1, "we")
        self.busy = Input(1, "busy")
        self.ready = Output(1, "ready")

        self.init = Reg(1, "init")

        self.prf = Array(64, 64, "prf")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.ready <<= 0
            with Else():
                self.ready <<= ~self.busy

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.prf[0] <<= 0
                self.prf[1] <<= 0
                self.prf[2] <<= 0
                self.prf[3] <<= 0
                self.prf[4] <<= 0
                self.prf[5] <<= 0
                self.prf[6] <<= 0
                self.prf[7] <<= 0
                self.prf[8] <<= 0
                self.prf[9] <<= 0
                self.prf[10] <<= 0
                self.prf[11] <<= 0
                self.prf[12] <<= 0
                self.prf[13] <<= 0
                self.prf[14] <<= 0
                self.prf[15] <<= 0
                self.prf[16] <<= 0
                self.prf[17] <<= 0
                self.prf[18] <<= 0
                self.prf[19] <<= 0
                self.prf[20] <<= 0
                self.prf[21] <<= 0
                self.prf[22] <<= 0
                self.prf[23] <<= 0
                self.prf[24] <<= 0
                self.prf[25] <<= 0
                self.prf[26] <<= 0
                self.prf[27] <<= 0
                self.prf[28] <<= 0
                self.prf[29] <<= 0
                self.prf[30] <<= 0
                self.prf[31] <<= 0
                self.prf[32] <<= 0
                self.prf[33] <<= 0
                self.prf[34] <<= 0
                self.prf[35] <<= 0
                self.prf[36] <<= 0
                self.prf[37] <<= 0
                self.prf[38] <<= 0
                self.prf[39] <<= 0
                self.prf[40] <<= 0
                self.prf[41] <<= 0
                self.prf[42] <<= 0
                self.prf[43] <<= 0
                self.prf[44] <<= 0
                self.prf[45] <<= 0
                self.prf[46] <<= 0
                self.prf[47] <<= 0
                self.prf[48] <<= 0
                self.prf[49] <<= 0
                self.prf[50] <<= 0
                self.prf[51] <<= 0
                self.prf[52] <<= 0
                self.prf[53] <<= 0
                self.prf[54] <<= 0
                self.prf[55] <<= 0
                self.prf[56] <<= 0
                self.prf[57] <<= 0
                self.prf[58] <<= 0
                self.prf[59] <<= 0
                self.prf[60] <<= 0
                self.prf[61] <<= 0
                self.prf[62] <<= 0
                self.prf[63] <<= 0
            with Else():
                self.init <<= 1
                with If((self.we == 1) & (self.busy == 0)):
                    self.prf[self.pr_waddr] <<= self.pr_wdata


