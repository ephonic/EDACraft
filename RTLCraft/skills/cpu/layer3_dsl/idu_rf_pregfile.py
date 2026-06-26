"""
L3 DSL — PRF, PRF.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PRF(Module):
    def __init__(self):
        super().__init__("prf")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rd_addr1 = Input(7, "rd_addr1")
        self.rd_addr2 = Input(7, "rd_addr2")
        self.wr_addr = Input(7, "wr_addr")
        self.wr_data = Input(64, "wr_data")
        self.wr_en = Input(1, "wr_en")
        self.rd_data1 = Output(64, "rd_data1")
        self.rd_data2 = Output(64, "rd_data2")

        self.init = Reg(1, "init")

        self.regs = Array(64, 64, "regs")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rd_data1 <<= 0
                self.rd_data2 <<= 0
            with Else():
                with If((self.rd_addr1 == 0)):
                    self.rd_data1 <<= 0
                with Else():
                    self.rd_data1 <<= self.regs[self.rd_addr1]
                with If((self.rd_addr2 == 0)):
                    self.rd_data2 <<= 0
                with Else():
                    self.rd_data2 <<= self.regs[self.rd_addr2]

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.regs[0] <<= 0
                self.regs[1] <<= 0
                self.regs[2] <<= 0
                self.regs[3] <<= 0
                self.regs[4] <<= 0
                self.regs[5] <<= 0
                self.regs[6] <<= 0
                self.regs[7] <<= 0
                self.regs[8] <<= 0
                self.regs[9] <<= 0
                self.regs[10] <<= 0
                self.regs[11] <<= 0
                self.regs[12] <<= 0
                self.regs[13] <<= 0
                self.regs[14] <<= 0
                self.regs[15] <<= 0
                self.regs[16] <<= 0
                self.regs[17] <<= 0
                self.regs[18] <<= 0
                self.regs[19] <<= 0
                self.regs[20] <<= 0
                self.regs[21] <<= 0
                self.regs[22] <<= 0
                self.regs[23] <<= 0
                self.regs[24] <<= 0
                self.regs[25] <<= 0
                self.regs[26] <<= 0
                self.regs[27] <<= 0
                self.regs[28] <<= 0
                self.regs[29] <<= 0
                self.regs[30] <<= 0
                self.regs[31] <<= 0
                self.regs[32] <<= 0
                self.regs[33] <<= 0
                self.regs[34] <<= 0
                self.regs[35] <<= 0
                self.regs[36] <<= 0
                self.regs[37] <<= 0
                self.regs[38] <<= 0
                self.regs[39] <<= 0
                self.regs[40] <<= 0
                self.regs[41] <<= 0
                self.regs[42] <<= 0
                self.regs[43] <<= 0
                self.regs[44] <<= 0
                self.regs[45] <<= 0
                self.regs[46] <<= 0
                self.regs[47] <<= 0
                self.regs[48] <<= 0
                self.regs[49] <<= 0
                self.regs[50] <<= 0
                self.regs[51] <<= 0
                self.regs[52] <<= 0
                self.regs[53] <<= 0
                self.regs[54] <<= 0
                self.regs[55] <<= 0
                self.regs[56] <<= 0
                self.regs[57] <<= 0
                self.regs[58] <<= 0
                self.regs[59] <<= 0
                self.regs[60] <<= 0
                self.regs[61] <<= 0
                self.regs[62] <<= 0
                self.regs[63] <<= 0
            with Else():
                self.init <<= 1
                with If((self.wr_en == 1) & (self.wr_addr != 0)):
                    self.regs[self.wr_addr] <<= self.wr_data


