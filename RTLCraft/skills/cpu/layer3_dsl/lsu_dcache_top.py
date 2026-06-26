"""
L3 DSL — DCacheTop, DCacheTop.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class DCacheTop(Module):
    def __init__(self):
        super().__init__("dcachetop")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(64, "req_addr")
        self.req_we = Input(1, "req_we")
        self.req_wdata = Input(64, "req_wdata")
        self.req_size = Input(4, "req_size")
        self.flush = Input(1, "flush")
        self.cache_fill_data = Input(128, "cache_fill_data")
        self.cache_fill_valid = Input(1, "cache_fill_valid")
        self.req_ready = Output(1, "req_ready")
        self.rdata = Output(64, "rdata")
        self.rvalid = Output(1, "rvalid")
        self.hit = Output(1, "hit")
        self.miss = Output(1, "miss")

        self.addr_r = Reg(64, "addr_r")
        self.data_rd = Wire(128, "data_rd")
        self.fill_set = Wire(6, "fill_set")
        self.fill_tag = Wire(54, "fill_tag")
        self.init = Reg(1, "init")
        self.req_tag = Wire(54, "req_tag")
        self.set_idx = Wire(6, "set_idx")
        self.state = Reg(1, "state")
        self.tag_hit = Wire(1, "tag_hit")
        self.tag_rd = Wire(54, "tag_rd")
        self.val_rd = Wire(1, "val_rd")

        self.tag = Array(54, 64, "tag")
        self.val = Array(1, 64, "val")
        self.data = Array(128, 64, "data")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.req_ready <<= 0
                self.rdata <<= 0
                self.rvalid <<= 0
                self.hit <<= 0
                self.miss <<= 0
            with Else():
                self.req_ready <<= (self.state == 0) & ~self.flush
                self.rdata <<= 0
                self.rvalid <<= 0
                with If((self.state == 0)):
                    with If((self.req_valid == 1)):
                        self.hit <<= self.tag_hit
                        self.miss <<= ~self.tag_hit
                        with If((self.tag_hit == 1) & (self.req_we == 0)):
                            with If((self.req_addr >> 4 & 1) == 0):
                                self.rdata <<= self.data_rd & 18446744073709551615
                            with Else():
                                self.rdata <<= self.data_rd >> 64
                            self.rvalid <<= 1
                    with Else():
                        self.hit <<= 0
                        self.miss <<= 0
                with Else():
                    self.miss <<= 1
                    self.hit <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.state <<= 0
                self.addr_r <<= 0
                self.val[0] <<= 0
                self.val[1] <<= 0
                self.val[2] <<= 0
                self.val[3] <<= 0
                self.val[4] <<= 0
                self.val[5] <<= 0
                self.val[6] <<= 0
                self.val[7] <<= 0
                self.val[8] <<= 0
                self.val[9] <<= 0
                self.val[10] <<= 0
                self.val[11] <<= 0
                self.val[12] <<= 0
                self.val[13] <<= 0
                self.val[14] <<= 0
                self.val[15] <<= 0
                self.val[16] <<= 0
                self.val[17] <<= 0
                self.val[18] <<= 0
                self.val[19] <<= 0
                self.val[20] <<= 0
                self.val[21] <<= 0
                self.val[22] <<= 0
                self.val[23] <<= 0
                self.val[24] <<= 0
                self.val[25] <<= 0
                self.val[26] <<= 0
                self.val[27] <<= 0
                self.val[28] <<= 0
                self.val[29] <<= 0
                self.val[30] <<= 0
                self.val[31] <<= 0
                self.val[32] <<= 0
                self.val[33] <<= 0
                self.val[34] <<= 0
                self.val[35] <<= 0
                self.val[36] <<= 0
                self.val[37] <<= 0
                self.val[38] <<= 0
                self.val[39] <<= 0
                self.val[40] <<= 0
                self.val[41] <<= 0
                self.val[42] <<= 0
                self.val[43] <<= 0
                self.val[44] <<= 0
                self.val[45] <<= 0
                self.val[46] <<= 0
                self.val[47] <<= 0
                self.val[48] <<= 0
                self.val[49] <<= 0
                self.val[50] <<= 0
                self.val[51] <<= 0
                self.val[52] <<= 0
                self.val[53] <<= 0
                self.val[54] <<= 0
                self.val[55] <<= 0
                self.val[56] <<= 0
                self.val[57] <<= 0
                self.val[58] <<= 0
                self.val[59] <<= 0
                self.val[60] <<= 0
                self.val[61] <<= 0
                self.val[62] <<= 0
                self.val[63] <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.state <<= 0
                    self.val[0] <<= 0
                    self.val[1] <<= 0
                    self.val[2] <<= 0
                    self.val[3] <<= 0
                    self.val[4] <<= 0
                    self.val[5] <<= 0
                    self.val[6] <<= 0
                    self.val[7] <<= 0
                    self.val[8] <<= 0
                    self.val[9] <<= 0
                    self.val[10] <<= 0
                    self.val[11] <<= 0
                    self.val[12] <<= 0
                    self.val[13] <<= 0
                    self.val[14] <<= 0
                    self.val[15] <<= 0
                    self.val[16] <<= 0
                    self.val[17] <<= 0
                    self.val[18] <<= 0
                    self.val[19] <<= 0
                    self.val[20] <<= 0
                    self.val[21] <<= 0
                    self.val[22] <<= 0
                    self.val[23] <<= 0
                    self.val[24] <<= 0
                    self.val[25] <<= 0
                    self.val[26] <<= 0
                    self.val[27] <<= 0
                    self.val[28] <<= 0
                    self.val[29] <<= 0
                    self.val[30] <<= 0
                    self.val[31] <<= 0
                    self.val[32] <<= 0
                    self.val[33] <<= 0
                    self.val[34] <<= 0
                    self.val[35] <<= 0
                    self.val[36] <<= 0
                    self.val[37] <<= 0
                    self.val[38] <<= 0
                    self.val[39] <<= 0
                    self.val[40] <<= 0
                    self.val[41] <<= 0
                    self.val[42] <<= 0
                    self.val[43] <<= 0
                    self.val[44] <<= 0
                    self.val[45] <<= 0
                    self.val[46] <<= 0
                    self.val[47] <<= 0
                    self.val[48] <<= 0
                    self.val[49] <<= 0
                    self.val[50] <<= 0
                    self.val[51] <<= 0
                    self.val[52] <<= 0
                    self.val[53] <<= 0
                    self.val[54] <<= 0
                    self.val[55] <<= 0
                    self.val[56] <<= 0
                    self.val[57] <<= 0
                    self.val[58] <<= 0
                    self.val[59] <<= 0
                    self.val[60] <<= 0
                    self.val[61] <<= 0
                    self.val[62] <<= 0
                    self.val[63] <<= 0
                with Elif((self.state == 0) & (self.req_valid == 1) & (self.tag_hit == 0)):
                    self.addr_r <<= self.req_addr
                    self.state <<= 1
                with Elif((self.state == 1) & (self.cache_fill_valid == 1)):
                    self.tag[self.fill_set] <<= self.fill_tag
                    self.val[self.fill_set] <<= 1
                    self.data[self.fill_set] <<= self.cache_fill_data
                    self.state <<= 0
                with If((self.state == 0) & (self.req_valid == 1) & (self.tag_hit == 1) & (self.req_we == 1)):
                    with If((self.req_addr >> 4 & 1) == 0):
                        self.data[self.set_idx] <<= self.data_rd & 340282366920938463444927863358058659840 | self.req_wdata
                    with Else():
                        self.data[self.set_idx] <<= self.data_rd & 18446744073709551615 | {self.req_wdata, 0}


